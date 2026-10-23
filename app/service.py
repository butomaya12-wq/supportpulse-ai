from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from . import models as m
from .telemetry import mark_audit_queued

GRACE = timedelta(minutes=30)


def as_utc(value: datetime) -> datetime:
    # SQLite may strip timezone info; persisted timestamps must be interpreted as UTC.
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def event_to_dict(ev: m.SourceEvent) -> dict:
    return {"id": ev.id, "external_id": ev.external_id, "kind": ev.kind,
            "event_time": as_utc(ev.event_time).isoformat(), "actor_id": ev.actor_id,
            "conversation_id": ev.conversation_id, "message": ev.message}


def audit(db: Session, tenant: str, actor: str, target: str, action: str,
          old: str | None = None, new: str | None = None, note: str | None = None):
    mark_audit_queued(action)
    db.add(m.Audit(tenant_id=tenant, actor=actor, target=target, action=action,
                   old_state=old, new_state=new, note=note))


def get_finding(db: Session, tenant: str, finding_id: int) -> m.Finding:
    finding = db.scalar(select(m.Finding).where(m.Finding.id == finding_id, m.Finding.tenant_id == tenant))
    if finding is None:
        raise HTTPException(404, "Case not found")
    return finding


def get_action(db: Session, tenant: str, action_id: int) -> m.CorrectiveAction:
    result = db.scalar(select(m.CorrectiveAction).where(m.CorrectiveAction.id == action_id, m.CorrectiveAction.tenant_id == tenant))
    if result is None:
        raise HTTPException(404, "Action not found")
    return result


def get_events_for_commitment(db: Session, c: m.Commitment) -> list[m.SourceEvent]:
    return list(db.scalars(select(m.SourceEvent).where(
        m.SourceEvent.tenant_id == c.tenant_id,
        m.SourceEvent.source_id == c.source_id,
        m.SourceEvent.conversation_id == c.conversation_id,
    ).order_by(m.SourceEvent.event_time, m.SourceEvent.id)).all())


def evaluate(db: Session, tenant: str, actor: str, as_of: datetime | None = None):
    as_of = as_utc(as_of or datetime.now(timezone.utc))
    updated = []
    for c in db.scalars(select(m.Commitment).where(m.Commitment.tenant_id == tenant, m.Commitment.state == "APPROVED")).all():
        source = db.scalar(select(m.Source).where(m.Source.id == c.source_id, m.Source.tenant_id == tenant))
        events = get_events_for_commitment(db, c)
        sent = next((ev for ev in events if ev.kind == "quote_sent" and ev.actor_id == c.actor_id), None)
        bounced = any(ev.kind == "quote_bounced" for ev in events)
        due = as_utc(c.due_at)
        if not source or source.health != "HEALTHY" or not source.watermark or as_utc(source.watermark) < due + GRACE:
            proposed = "INSUFFICIENT_DATA"
        elif sent and as_utc(sent.event_time) <= due:
            proposed = "SENT_UNCONFIRMED_DELIVERY" if bounced else "ON_TIME"
        elif sent:
            proposed = "SENT_UNCONFIRMED_DELIVERY" if bounced else "FULFILLED_LATE"
        elif as_of >= due + GRACE:
            proposed = "CANDIDATE_OVERDUE"
        else:
            proposed = "NOT_DUE"
        finding = db.scalar(select(m.Finding).where(m.Finding.tenant_id == tenant, m.Finding.commitment_id == c.id))
        if not finding:
            finding = m.Finding(tenant_id=tenant, commitment_id=c.id, state=proposed)
            db.add(finding)
            db.flush()
            audit(db, tenant, actor, f"finding:{finding.id}", "EVALUATED", new=proposed)
        elif finding.state != proposed:
            # Never silently overturn human decisions except when new evidence arrives.
            changed_on_evidence = sent is not None and proposed in ("ON_TIME", "FULFILLED_LATE", "SENT_UNCONFIRMED_DELIVERY")
            if finding.state in ("CONFIRMED_OVERDUE", "DISMISSED", "CORRECTED_LATE") and not changed_on_evidence:
                updated.append({"finding_id": finding.id, "state": finding.state})
                continue
            if finding.state == "CORRECTED_LATE" and proposed == "FULFILLED_LATE":
                updated.append({"finding_id": finding.id, "state": finding.state})
                continue
            old = finding.state
            finding.state = proposed
            finding.evidence_event_id = sent.id if sent else None
            finding.revision += 1
            audit(db, tenant, actor, f"finding:{finding.id}", "RE_EVALUATED", old, proposed)
        updated.append({"finding_id": finding.id, "state": finding.state})
    db.commit()
    return updated



def verification_readiness(db: Session, f: m.Finding, c: m.Commitment, action: m.CorrectiveAction | None) -> dict:
    """Suggest matching source evidence; the verify endpoint remains authoritative."""
    if action is None:
        return {"ready": False, "proof_external_id": None, "reason": "NO_ACTION"}
    if action.state == "VERIFIED":
        return {"ready": False, "proof_external_id": None, "reason": "ALREADY_VERIFIED"}
    if f.state not in ("CONFIRMED_OVERDUE", "FULFILLED_LATE", "SENT_UNCONFIRMED_DELIVERY"):
        return {"ready": False, "proof_external_id": None, "reason": "CASE_NOT_VERIFIABLE"}
    events = get_events_for_commitment(db, c)
    if any(e.kind == "quote_bounced" for e in events):
        return {"ready": False, "proof_external_id": None, "reason": "BOUNCED"}
    sent = next((e for e in events if e.kind == "quote_sent" and e.actor_id == c.actor_id), None)
    if sent is None:
        return {"ready": False, "proof_external_id": None, "reason": "NO_SOURCE_PROOF"}
    return {"ready": True, "proof_external_id": sent.external_id, "reason": "PROOF_AVAILABLE"}

def finding_detail(db: Session, f: m.Finding) -> dict:
    c = db.get(m.Commitment, f.commitment_id)
    basis = db.get(m.SourceEvent, c.basis_event_id)
    action = db.scalar(select(m.CorrectiveAction).where(m.CorrectiveAction.finding_id == f.id, m.CorrectiveAction.tenant_id == f.tenant_id))
    return {"id": f.id, "state": f.state, "revision": f.revision,
            "commitment": {"id": c.id, "action": c.action_type, "actor_id": c.actor_id,
                           "conversation_id": c.conversation_id, "due_at": as_utc(c.due_at).isoformat(),
                           "approved": c.state == "APPROVED", "basis": event_to_dict(basis)},
            "evidence": [event_to_dict(ev) for ev in get_events_for_commitment(db, c)],
            "review": {"by": f.reviewed_by, "reason": f.review_reason} if f.reviewed_by else None,
            "corrective_action": {"id": action.id, "owner_id": action.owner_id, "state": action.state,
                                  "proof_event_id": action.proof_event_id} if action else None,
            "verification": verification_readiness(db, f, c, action),
            "quality_state": "INSUFFICIENT_DATA" if f.state == "INSUFFICIENT_DATA" else "VALID",
            "impact_rub": None, "ai_inferred": False}


def overview(db: Session, tenant: str) -> dict:
    states = {state: count for state, count in db.execute(select(m.Finding.state, func.count(m.Finding.id)).where(
        m.Finding.tenant_id == tenant).group_by(m.Finding.state)).all()}
    on_time = states.get("ON_TIME", 0)
    overdue = states.get("CONFIRMED_OVERDUE", 0) + states.get("CORRECTED_LATE", 0) + states.get("FULFILLED_LATE", 0)
    denom = on_time + overdue
    sources = db.scalars(select(m.Source).where(m.Source.tenant_id == tenant)).all()
    verified = db.scalar(select(func.count()).select_from(m.CorrectiveAction).where(
        m.CorrectiveAction.tenant_id == tenant, m.CorrectiveAction.state == "VERIFIED")) or 0
    total_actions = db.scalar(select(func.count()).select_from(m.CorrectiveAction).where(m.CorrectiveAction.tenant_id == tenant)) or 0
    human_confirmed = db.scalar(select(func.count()).select_from(m.Finding).where(
        m.Finding.tenant_id == tenant, m.Finding.reviewed_by.is_not(None),
        m.Finding.state.in_(("CONFIRMED_OVERDUE", "FULFILLED_LATE", "CORRECTED_LATE")))) or 0
    return {"tenant": tenant, "data_mode": "SYNTHETIC_ONLY", "impact_rub": None,
            "counts": {"review_backlog": states.get("CANDIDATE_OVERDUE", 0) + states.get("INSUFFICIENT_DATA", 0),
                       "confirmed_overdue": human_confirmed,
                       "unknown": states.get("INSUFFICIENT_DATA", 0),
                       "actions_verified": verified, "actions_total": total_actions},
            "on_time": {"value": round(on_time / denom, 4) if denom else None,
                        "numerator": on_time, "denominator": denom, "excluded_unknown": states.get("INSUFFICIENT_DATA", 0),
                        "quality_state": "VALID" if denom else "INSUFFICIENT_DATA"},
            "sources": [{"id": s.id, "channel": s.channel, "health": s.health,
                         "watermark": as_utc(s.watermark).isoformat() if s.watermark else None} for s in sources],
            "states": states}
