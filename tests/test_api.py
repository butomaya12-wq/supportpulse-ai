from datetime import datetime, timezone
import copy
from app.models import Source, Finding


def submit(c, headers, initial):
    r=c.post('/api/v1/imports',headers=headers,json=initial['import'])
    assert r.status_code==200, r.text
    r=c.post('/api/v1/commitments',headers=headers,json=initial['commitment'])
    assert r.status_code==200, r.text
    r=c.post('/api/v1/evaluate',headers=headers,params={'as_of':initial['evaluate_as_of']})
    assert r.status_code==200, r.text
    return r.json()['findings'][0]['finding_id']


def test_no_unauthenticated_access(ctx):
    c,_=ctx
    assert c.get('/api/v1/findings').status_code==401
    assert c.get('/api/v1/findings',headers={'Authorization':'Bearer wrong'}).status_code==401
    assert c.get('/health').json()['production_ready'] is False


def test_seed_and_full_human_workflow(ctx,supervisor):
    c,_=ctx
    assert c.post('/api/v1/demo/seed',headers=supervisor).status_code==200
    found=c.get('/api/v1/findings',headers=supervisor).json()['data'][0]
    assert found['state']=='CANDIDATE_OVERDUE'
    assert found['commitment']['basis']['external_id']=='msg-002'
    assert found['impact_rub'] is None and found['ai_inferred'] is False
    n=found['id']
    assert c.post(f'/api/v1/findings/{n}/review',headers=supervisor,json={'decision':'CONFIRM','reason':'No outbound quote seen with complete sync'}).json()['state']=='CONFIRMED_OVERDUE'
    action=c.post(f'/api/v1/findings/{n}/actions',headers=supervisor,json={'owner_id':'demo-manager-001'}).json()
    assert action['created'] is True
    assert c.post(f'/api/v1/actions/{action["action_id"]}/verify',headers=supervisor,json={'proof_external_id':'invented'}).status_code==409
    r=c.post('/api/v1/demo/followup',headers=supervisor)
    assert r.status_code==200, r.text
    assert c.get(f'/api/v1/findings/{n}',headers=supervisor).json()['state']=='FULFILLED_LATE'
    assert c.get('/api/v1/overview',headers=supervisor).json()['counts']['confirmed_overdue']==1
    verified=c.post(f'/api/v1/actions/{action["action_id"]}/verify',headers=supervisor,json={'proof_external_id':'msg-003'})
    assert verified.status_code==200, verified.text
    assert verified.json()['delivery_confirmed'] is False
    assert c.get(f'/api/v1/findings/{n}',headers=supervisor).json()['state']=='CORRECTED_LATE'
    o=c.get('/api/v1/overview',headers=supervisor).json()
    assert o['counts']['actions_verified']==1
    assert o['impact_rub'] is None
    logs=c.get('/api/v1/audit',headers=supervisor).json()['data']
    assert any(x['action']=='ACTION_CLOSED' for x in logs)
    assert c.post('/api/v1/demo/seed',headers=supervisor).status_code==409 # watermark would regress after followup


def test_reimport_idempotent(ctx,supervisor,initial):
    c,_=ctx
    x=c.post('/api/v1/imports',headers=supervisor,json=initial['import'])
    y=c.post('/api/v1/imports',headers=supervisor,json=initial['import'])
    assert x.json()['inserted']==2
    assert y.json()['inserted']==0 and y.json()['deduplicated']==2
    a=c.post('/api/v1/commitments',headers=supervisor,json=initial['commitment']).json()
    b=c.post('/api/v1/commitments',headers=supervisor,json=initial['commitment']).json()
    assert a['created'] and not b['created']
    c.post('/api/v1/evaluate',headers=supervisor,params={'as_of':initial['evaluate_as_of']})
    c.post('/api/v1/evaluate',headers=supervisor,params={'as_of':initial['evaluate_as_of']})
    assert len(c.get('/api/v1/findings',headers=supervisor).json()['data'])==1


def test_immutable_provider_events(ctx,supervisor,initial):
    c,_=ctx
    assert c.post('/api/v1/imports',headers=supervisor,json=initial['import']).status_code==200
    bad=copy.deepcopy(initial['import']);bad['events'][0]['message']='Modified provider evidence'
    assert c.post('/api/v1/imports',headers=supervisor,json=bad).status_code==409
    assert c.get('/api/v1/overview',headers=supervisor).status_code==200


def test_missing_watermark_protects_manager(ctx,supervisor,initial):
    c,_=ctx
    initial['import']['watermark']='2026-10-22T13:05:00Z' # due 13:00, grace until 13:30
    n=submit(c,supervisor,initial)
    f=c.get(f'/api/v1/findings/{n}',headers=supervisor).json()
    assert f['state']=='INSUFFICIENT_DATA'
    assert c.post(f'/api/v1/findings/{n}/review',headers=supervisor,json={'decision':'CONFIRM','reason':'Wrong: missing coverage'}).status_code==409


def test_degraded_source_does_not_accuse(ctx,supervisor,initial):
    c,_=ctx
    initial['import']['healthy']=False
    n=submit(c,supervisor,initial)
    assert c.get(f'/api/v1/findings/{n}',headers=supervisor).json()['state']=='INSUFFICIENT_DATA'


def test_on_time_evidence_prevents_false_alert(ctx,supervisor,initial):
    c,_=ctx
    initial['import']['events'].append({'external_id':'sent-before','event_time':'2026-10-22T12:00:00Z','kind':'quote_sent','conversation_id':'demo-lead-001','actor_id':'demo-manager-001','message':'Sent quote'})
    n=submit(c,supervisor,initial)
    assert c.get(f'/api/v1/findings/{n}',headers=supervisor).json()['state']=='ON_TIME'
    o=c.get('/api/v1/overview',headers=supervisor).json()
    assert o['on_time']['value']==1.0
    assert o['on_time']['denominator']==1


def test_manager_scoped_and_cannot_review(ctx,supervisor,manager,initial):
    c,_=ctx
    n=submit(c,supervisor,initial)
    assert c.post(f'/api/v1/findings/{n}/review',headers=manager,json={'decision':'CONFIRM','reason':'I want to approve myself'}).status_code==403
    assert c.get('/api/v1/audit',headers=manager).status_code==403
    assert len(c.get('/api/v1/findings',headers=manager).json()['data'])==1
    assert c.post('/api/v1/imports',headers=manager,json=initial['import']).status_code==403


def test_cross_tenant_case_not_exposed(ctx,supervisor):
    c,Session=ctx
    with Session.begin() as db:
        db.add(Source(id='other-source',tenant_id='other-tenant',channel='other'))
        db.add(Finding(id=777,tenant_id='other-tenant',commitment_id=800, state='CANDIDATE_OVERDUE'))
    assert c.get('/api/v1/findings/777',headers=supervisor).status_code==404


def test_naive_timestamps_and_watermark_regression_rejected(ctx,supervisor,initial):
    c,_=ctx
    payload=copy.deepcopy(initial['import'])
    payload['watermark']='2026-10-22T14:00:00'
    assert c.post('/api/v1/imports',headers=supervisor,json=payload).status_code==422
    payload=copy.deepcopy(initial['import'])
    assert c.post('/api/v1/imports',headers=supervisor,json=payload).status_code==200
    payload['watermark']='2026-10-22T13:30:00Z'
    assert c.post('/api/v1/imports',headers=supervisor,json=payload).status_code==409


def test_review_requires_explicit_reason(ctx,supervisor,initial):
    c,_=ctx
    n=submit(c,supervisor,initial)
    assert c.post(f'/api/v1/findings/{n}/review',headers=supervisor,json={'decision':'CONFIRM','reason':'bad'}).status_code==422
    assert c.post(f'/api/v1/findings/{n}/review',headers=supervisor,json={'decision':'DISMISS','reason':'Client cancellation independently confirmed'}).json()['state']=='DISMISSED'
    assert c.post(f'/api/v1/findings/{n}/actions',headers=supervisor,json={'owner_id':'demo-manager-001'}).status_code==409


def test_empty_overview_keeps_unknown_not_zero(ctx,supervisor):
    c,_=ctx
    data=c.get('/api/v1/overview',headers=supervisor).json()
    assert data['on_time']['value'] is None
    assert data['on_time']['denominator']==0
    assert data['impact_rub'] is None


def test_manager_can_verify_only_own_assigned_action(ctx,supervisor,manager):
    c,_=ctx
    seeded=c.post('/api/v1/demo/seed',headers=supervisor).json()
    n=seeded['evaluation']['findings'][0]['finding_id']
    c.post(f'/api/v1/findings/{n}/review',headers=supervisor,json={'decision':'CONFIRM','reason':'Provider history contains no quote within the approved window'})
    a=c.post(f'/api/v1/findings/{n}/actions',headers=supervisor,json={'owner_id':'demo-manager-001'}).json()['action_id']
    c.post('/api/v1/demo/followup',headers=supervisor)
    assert c.post(f'/api/v1/actions/{a}/verify',headers=manager,json={'proof_external_id':'msg-003'}).status_code==200
    assert c.post(f'/api/v1/actions/{a}/verify',headers=manager,json={'proof_external_id':'msg-003'}).json()['created'] is False


def test_bounced_quote_never_counted_as_corrected(ctx,supervisor,initial):
    c,_=ctx
    n=submit(c,supervisor,initial)
    c.post(f'/api/v1/findings/{n}/review',headers=supervisor,json={'decision':'CONFIRM','reason':'Promise missed from healthy source'})
    action_id=c.post(f'/api/v1/findings/{n}/actions',headers=supervisor,json={'owner_id':'demo-manager-001'}).json()['action_id']
    payload={'source_id':'demo-instagram','channel':'instagram-synthetic','watermark':'2026-10-22T15:00:00Z','healthy':True,'events':[
      {'external_id':'sent-001','event_time':'2026-10-22T14:12:00Z','kind':'quote_sent','conversation_id':'demo-lead-001','actor_id':'demo-manager-001','message':'Sent quotation'},
      {'external_id':'bounce-001','event_time':'2026-10-22T14:15:00Z','kind':'quote_bounced','conversation_id':'demo-lead-001','actor_id':'demo-manager-001','message':'Delivery failure'}
    ]}
    assert c.post('/api/v1/imports',headers=supervisor,json=payload).status_code==200
    c.post('/api/v1/evaluate',headers=supervisor,params={'as_of':'2026-10-22T15:00:00Z'})
    assert c.get(f'/api/v1/findings/{n}',headers=supervisor).json()['state']=='SENT_UNCONFIRMED_DELIVERY'
    assert c.post(f'/api/v1/actions/{action_id}/verify',headers=supervisor,json={'proof_external_id':'sent-001'}).status_code==409


def test_verification_requires_matching_source_proof(ctx, supervisor):
    c, _ = ctx
    n = c.post('/api/v1/demo/seed', headers=supervisor).json()['evaluation']['findings'][0]['finding_id']
    c.post(f'/api/v1/findings/{n}/review', headers=supervisor,
           json={'decision': 'CONFIRM', 'reason': 'No valid source evidence of on-time send'})
    action = c.post(f'/api/v1/findings/{n}/actions', headers=supervisor,
                    json={'owner_id': 'demo-manager-001'}).json()['action_id']
    before = c.get(f'/api/v1/findings/{n}', headers=supervisor).json()
    assert before['verification'] == {'ready': False, 'proof_external_id': None, 'reason': 'NO_SOURCE_PROOF'}
    assert c.post(f'/api/v1/actions/{action}/verify', headers=supervisor,
                  json={'proof_external_id': 'msg-003'}).status_code == 409
    assert c.post('/api/v1/demo/followup', headers=supervisor).status_code == 200
    after = c.get(f'/api/v1/findings/{n}', headers=supervisor).json()
    assert after['verification'] == {'ready': True, 'proof_external_id': 'msg-003', 'reason': 'PROOF_AVAILABLE'}
    assert c.post(f'/api/v1/actions/{action}/verify', headers=supervisor,
                  json={'proof_external_id': 'msg-002'}).status_code == 409
    assert c.post(f'/api/v1/actions/{action}/verify', headers=supervisor,
                  json={'proof_external_id': 'msg-003'}).status_code == 200
    done = c.get(f'/api/v1/findings/{n}', headers=supervisor).json()
    assert done['verification']['reason'] == 'ALREADY_VERIFIED'
    assert done['corrective_action']['state'] == 'VERIFIED'


def test_bounced_evidence_not_eligible_for_verification(ctx, supervisor, initial):
    c, _ = ctx
    n = submit(c, supervisor, initial)
    c.post(f'/api/v1/findings/{n}/review', headers=supervisor,
           json={'decision': 'CONFIRM', 'reason': 'Promised quote missing from healthy source'})
    c.post(f'/api/v1/findings/{n}/actions', headers=supervisor,
           json={'owner_id': 'demo-manager-001'})
    followup = {'source_id': 'demo-instagram', 'channel': 'instagram-synthetic',
                'watermark': '2026-10-22T15:00:00Z', 'healthy': True, 'events': [
                   {'external_id': 's1', 'event_time': '2026-10-22T14:12:00Z', 'kind': 'quote_sent',
                    'conversation_id': 'demo-lead-001', 'actor_id': 'demo-manager-001', 'message': 'quote sent'},
                   {'external_id': 'b1', 'event_time': '2026-10-22T14:15:00Z', 'kind': 'quote_bounced',
                    'conversation_id': 'demo-lead-001', 'actor_id': 'demo-manager-001', 'message': 'quote bounced'}]}
    assert c.post('/api/v1/imports', headers=supervisor, json=followup).status_code == 200
    c.post('/api/v1/evaluate', headers=supervisor, params={'as_of': '2026-10-22T15:00:00Z'})
    f = c.get(f'/api/v1/findings/{n}', headers=supervisor).json()
    assert f['verification']['ready'] is False
    assert f['verification']['reason'] == 'BOUNCED'
