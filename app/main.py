"""SupportPulse synthetic-only vertical slice. No real tenant credentials or customer data."""
import json
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from . import models as m
from .auth import DEMO_TENANT, Principal, require_user, supervisor_only
from .db import Base, engine, db_session
from .schemas import ImportIn, CommitmentIn, ReviewIn, AssignIn, VerifyIn, AIProposalsIn
from .service import as_utc, audit, evaluate, finding_detail, get_action, get_finding, overview
from .ai_extract import provider_name, propose

ROOT = Path(__file__).resolve().parent.parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.environ.get("SP_MODE", "synthetic_local") != "synthetic_local":
        raise RuntimeError("Production operation is intentionally disabled; this is a local synthetic demo")
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="SupportPulse AI", version="0.1.0", lifespan=lifespan,
              description="Local synthetic-only testbed; not a production service")


@app.get("/")
def home():
    return FileResponse(ROOT / "app" / "static" / "index.html")


@app.get("/ui.js")
def ui_js():
    return FileResponse(ROOT / "app" / "static" / "ui.js", media_type="text/javascript")


@app.get("/style.css")
def styles():
    return FileResponse(ROOT / "app" / "static" / "style.css", media_type="text/css")


@app.get("/health")
def health():
    return {"status": "ok", "data_mode": "SYNTHETIC_ONLY", "production_ready": False}


@app.get("/api/v1/me")
def me(user: Principal = Depends(require_user)):
    return {"actor": user.actor, "role": user.role, "tenant": user.tenant_id, "data_mode": "SYNTHETIC_ONLY"}


@app.post("/api/v1/imports")
def import_events(payload: ImportIn, user: Principal = Depends(require_user), db: Session = Depends(db_session)):
    supervisor_only(user)
    for e in payload.events:
        if e.event_time.tzinfo is None or e.event_time.utcoffset() is None:
            raise HTTPException(422, "Event timestamps require a timezone")
    if payload.watermark.tzinfo is None or payload.watermark.utcoffset() is None:
        raise HTTPException(422, "Watermark requires a timezone")
    if any(as_utc(e.event_time) > as_utc(payload.watermark) for e in payload.events):
        raise HTTPException(422, "Watermark cannot predate an imported event")
    source = db.scalar(select(m.Source).where(m.Source.id == payload.source_id, m.Source.tenant_id == user.tenant_id))
    if source is None:
        # Prevent a caller from reusing another tenant's identifier.
        if db.get(m.Source, payload.source_id):
            raise HTTPException(409, "Source identifier unavailable")
        source = m.Source(id=payload.source_id, tenant_id=user.tenant_id, channel=payload.channel)
        db.add(source)
        db.flush()
    elif source.channel != payload.channel:
        raise HTTPException(409, "Existing source channel cannot change")
    if source.watermark and as_utc(payload.watermark) < as_utc(source.watermark):
        raise HTTPException(409, "Watermark cannot move backward")
    inserted = 0
    for e in payload.events:
        existing = db.scalar(select(m.SourceEvent).where(m.SourceEvent.tenant_id == user.tenant_id,
                            m.SourceEvent.source_id == payload.source_id, m.SourceEvent.external_id == e.external_id))
        if existing:
            if (existing.kind != e.kind or existing.message != e.message
                    or existing.conversation_id != e.conversation_id or existing.actor_id != e.actor_id
                    or as_utc(existing.event_time) != as_utc(e.event_time)):
                db.rollback()
                raise HTTPException(409, f"Conflicting immutable provider event {e.external_id}")
            continue
        db.add(m.SourceEvent(tenant_id=user.tenant_id, source_id=source.id, external_id=e.external_id,
                             event_time=as_utc(e.event_time), kind=e.kind,
                             conversation_id=e.conversation_id, actor_id=e.actor_id, message=e.message))
        inserted += 1
    source.watermark = as_utc(payload.watermark)
    source.health = "HEALTHY" if payload.healthy else "DEGRADED"
    audit(db, user.tenant_id, user.actor, f"source:{source.id}", "IMPORT", note=f"inserted={inserted}; synthetic only")
    db.commit()
    return {"inserted": inserted, "deduplicated": len(payload.events) - inserted,
            "watermark": as_utc(source.watermark).isoformat(), "data_mode": "SYNTHETIC_ONLY"}




@app.post("/api/v1/ai/proposals")
def ai_promise_proposals(payload: AIProposalsIn, user: Principal = Depends(require_user),
                         db: Session = Depends(db_session)):
    """Read-only candidate extraction; only the separate human approval API writes commitments."""
    supervisor_only(user)
    provider = provider_name()
    source = db.scalar(select(m.Source).where(
        m.Source.id == payload.source_id, m.Source.tenant_id == user.tenant_id))
    if source is None:
        raise HTTPException(404, "Source not found")
    envelope = {
        "source_id": payload.source_id,
        "conversation_id": payload.conversation_id,
        "provider": "RULE_BASELINE_NOT_AI" if provider == "rules" else provider.upper(),
        "external_model_invoked": provider == "openai",
        "review_required": True,
        "data_mode": "SYNTHETIC_ONLY",
        "proposals": [],
        "abstentions": [],
    }
    if source.health != "HEALTHY" or source.watermark is None:
        envelope["abstentions"] = [{"reason": "INSUFFICIENT_SOURCE_COVERAGE"}]
        return envelope
    events = db.scalars(select(m.SourceEvent).where(
        m.SourceEvent.tenant_id == user.tenant_id,
        m.SourceEvent.source_id == source.id,
        m.SourceEvent.conversation_id == payload.conversation_id,
        m.SourceEvent.kind == "manager_message"
    ).order_by(m.SourceEvent.event_time, m.SourceEvent.id).limit(8)).all()
    for ev in events:
        item = {"basis_external_id": ev.external_id}
        if as_utc(ev.event_time) > as_utc(source.watermark):
            item["reason"] = "EVENT_NOT_COVERED"
            envelope["abstentions"].append(item)
            continue
        if len(ev.message) > 2000:
            item["reason"] = "MESSAGE_TOO_LONG"
            envelope["abstentions"].append(item)
            continue
        result = propose(ev.message, as_utc(ev.event_time), provider)
        if result["status"] == "PROPOSED":
            envelope["proposals"].append({
                "source_id": source.id,
                "conversation_id": payload.conversation_id,
                "basis_external_id": ev.external_id,
                "actor_id": ev.actor_id,
                "evidence_quote": result["quote"],
                "due_at": result["due_at"],
                "action_type": result["action_type"],
                "status": "PROPOSED_NOT_APPROVED",
                "confidence": None,
                "financial_impact": None,
            })
        else:
            item["reason"] = result["reason"]
            envelope["abstentions"].append(item)
    if not events:
        envelope["abstentions"].append({"reason": "NO_MANAGER_MESSAGES"})
    return envelope

@app.post("/api/v1/commitments")
def approve_commitment(payload: CommitmentIn, user: Principal = Depends(require_user), db: Session = Depends(db_session)):
    supervisor_only(user)
    if payload.due_at.tzinfo is None or payload.due_at.utcoffset() is None:
        raise HTTPException(422, "Explicit timezone required for deadline")
    basis = db.scalar(select(m.SourceEvent).where(m.SourceEvent.tenant_id == user.tenant_id,
                      m.SourceEvent.source_id == payload.source_id, m.SourceEvent.external_id == payload.basis_external_id))
    if not basis or basis.kind != "manager_message":
        raise HTTPException(404, "Manager promise evidence not found")
    c = db.scalar(select(m.Commitment).where(m.Commitment.tenant_id == user.tenant_id,
                  m.Commitment.basis_event_id == basis.id, m.Commitment.action_type == payload.action_type))
    if c:
        if as_utc(c.due_at) != as_utc(payload.due_at):
            raise HTTPException(409, "Approved commitment exists with a different deadline")
        return {"commitment_id": c.id, "created": False, "state": c.state}
    c = m.Commitment(tenant_id=user.tenant_id, source_id=basis.source_id,
                     conversation_id=basis.conversation_id, actor_id=basis.actor_id,
                     action_type=payload.action_type, due_at=as_utc(payload.due_at),
                     basis_event_id=basis.id, state="APPROVED")
    db.add(c)
    db.flush()
    audit(db, user.tenant_id, user.actor, f"commitment:{c.id}", "HUMAN_APPROVED", new="APPROVED")
    db.commit()
    return {"commitment_id": c.id, "created": True, "state": c.state}


@app.post("/api/v1/evaluate")
def run_evaluation(as_of: datetime | None = None, user: Principal = Depends(require_user), db: Session = Depends(db_session)):
    supervisor_only(user)
    if as_of and (as_of.tzinfo is None or as_of.utcoffset() is None):
        raise HTTPException(422, "Evaluation time requires timezone")
    return {"findings": evaluate(db, user.tenant_id, user.actor, as_of)}


@app.get("/api/v1/overview")
def get_overview(user: Principal = Depends(require_user), db: Session = Depends(db_session)):
    supervisor_only(user)
    return overview(db, user.tenant_id)


@app.get("/api/v1/findings")
def list_findings(user: Principal = Depends(require_user), db: Session = Depends(db_session),
                  state: str | None = None, limit: int = Query(default=50, ge=1, le=100)):
    q = select(m.Finding).where(m.Finding.tenant_id == user.tenant_id)
    if state:
        q = q.where(m.Finding.state == state)
    findings = db.scalars(q.order_by(m.Finding.id.desc()).limit(limit)).all()
    details = [finding_detail(db, f) for f in findings]
    if user.role == "manager":
        details = [d for d in details if d["commitment"]["actor_id"] == user.actor]
    return {"data": details, "quality_state": "VALID", "impact_rub": None}


@app.get("/api/v1/findings/{finding_id}")
def show_finding(finding_id: int, user: Principal = Depends(require_user), db: Session = Depends(db_session)):
    result = finding_detail(db, get_finding(db, user.tenant_id, finding_id))
    if user.role == "manager" and result["commitment"]["actor_id"] != user.actor:
        raise HTTPException(404, "Case not found")
    return result


@app.post("/api/v1/findings/{finding_id}/review")
def review_finding(finding_id: int, payload: ReviewIn, user: Principal = Depends(require_user), db: Session = Depends(db_session)):
    supervisor_only(user)
    f = get_finding(db, user.tenant_id, finding_id)
    if f.state != "CANDIDATE_OVERDUE":
        raise HTTPException(409, "Only candidate overdue findings can be reviewed")
    old = f.state
    f.state = "CONFIRMED_OVERDUE" if payload.decision == "CONFIRM" else "DISMISSED"
    f.reviewed_by = user.actor
    f.review_reason = payload.reason
    f.revision += 1
    audit(db, user.tenant_id, user.actor, f"finding:{f.id}", "HUMAN_REVIEW", old, f.state, payload.reason)
    db.commit()
    return {"id": f.id, "state": f.state}


@app.post("/api/v1/findings/{finding_id}/actions")
def assign_action(finding_id: int, payload: AssignIn, user: Principal = Depends(require_user), db: Session = Depends(db_session)):
    supervisor_only(user)
    f = get_finding(db, user.tenant_id, finding_id)
    if f.state != "CONFIRMED_OVERDUE":
        raise HTTPException(409, "Supervisor confirmation required before action")
    existing = db.scalar(select(m.CorrectiveAction).where(m.CorrectiveAction.tenant_id == user.tenant_id,
                         m.CorrectiveAction.finding_id == finding_id))
    if existing:
        if existing.owner_id != payload.owner_id:
            raise HTTPException(409, "Existing action has a different owner")
        return {"action_id": existing.id, "state": existing.state, "created": False}
    action = m.CorrectiveAction(tenant_id=user.tenant_id, finding_id=f.id,
                                owner_id=payload.owner_id, state="OPEN")
    db.add(action)
    db.flush()
    audit(db, user.tenant_id, user.actor, f"action:{action.id}", "ASSIGNED", new="OPEN")
    db.commit()
    return {"action_id": action.id, "state": action.state, "created": True}


@app.post("/api/v1/actions/{action_id}/verify")
def verify_action(action_id: int, payload: VerifyIn, user: Principal = Depends(require_user), db: Session = Depends(db_session)):
    action = get_action(db, user.tenant_id, action_id)
    if user.role != "supervisor" and user.actor != action.owner_id:
        raise HTTPException(403, "Action ownership required")
    f = get_finding(db, user.tenant_id, action.finding_id)
    c = db.get(m.Commitment, f.commitment_id)
    proof = db.scalar(select(m.SourceEvent).where(m.SourceEvent.tenant_id == user.tenant_id,
                      m.SourceEvent.source_id == c.source_id, m.SourceEvent.external_id == payload.proof_external_id))
    if not proof or proof.kind != "quote_sent" or proof.conversation_id != c.conversation_id or proof.actor_id != c.actor_id:
        raise HTTPException(409, "Verified provider quote_sent event required for this conversation and actor")
    if action.state == "VERIFIED":
        if action.proof_event_id == proof.id:
            return {"action_id": action.id, "state": "VERIFIED", "created": False}
        raise HTTPException(409, "Action already verified against another event")
    if f.state not in ("CONFIRMED_OVERDUE", "FULFILLED_LATE", "SENT_UNCONFIRMED_DELIVERY"):
        raise HTTPException(409, "Action no longer verifiable in current finding state")
    bounced = db.scalar(select(m.SourceEvent.id).where(m.SourceEvent.tenant_id == user.tenant_id,
                         m.SourceEvent.source_id == c.source_id, m.SourceEvent.conversation_id == c.conversation_id,
                         m.SourceEvent.kind == "quote_bounced").limit(1))
    if bounced:
        raise HTTPException(409, "Quote bounced; cannot verify corrective success")
    action.state = "VERIFIED"
    action.proof_event_id = proof.id
    old = f.state
    f.state = "CORRECTED_LATE" if as_utc(proof.event_time) > as_utc(c.due_at) else "ON_TIME"
    f.revision += 1
    audit(db, user.tenant_id, user.actor, f"action:{action.id}", "PROVIDER_PROOF_VERIFIED", "OPEN", "VERIFIED", proof.external_id)
    audit(db, user.tenant_id, user.actor, f"finding:{f.id}", "ACTION_CLOSED", old, f.state)
    db.commit()
    return {"action_id": action.id, "state": "VERIFIED", "delivery_confirmed": False}


@app.get("/api/v1/audit")
def get_audit(user: Principal = Depends(require_user), db: Session = Depends(db_session)):
    supervisor_only(user)
    logs = db.scalars(select(m.Audit).where(m.Audit.tenant_id == user.tenant_id).order_by(m.Audit.id.desc()).limit(100)).all()
    return {"data": [{"id": x.id, "actor": x.actor, "target": x.target, "action": x.action,
                       "old": x.old_state, "new": x.new_state, "time": x.at.isoformat(), "note": x.note} for x in logs]}


@app.post("/api/v1/demo/seed")
def seed_synthetic(user: Principal = Depends(require_user), db: Session = Depends(db_session)):
    supervisor_only(user)
    p = json.loads((ROOT / "fixtures" / "initial.json").read_text(encoding="utf-8"))
    imported = import_events(ImportIn.model_validate(p["import"]), user, db)
    approved = approve_commitment(CommitmentIn.model_validate(p["commitment"]), user, db)
    evaluated = run_evaluation(datetime.fromisoformat(p["evaluate_as_of"]), user, db)
    return {"import": imported, "approved": approved, "evaluation": evaluated, "fixture": "SYNTHETIC"}


@app.post("/api/v1/demo/followup")
def synthetic_followup(user: Principal = Depends(require_user), db: Session = Depends(db_session)):
    supervisor_only(user)
    p = json.loads((ROOT / "fixtures" / "followup.json").read_text(encoding="utf-8"))
    imported = import_events(ImportIn.model_validate(p["import"]), user, db)
    evaluated = run_evaluation(datetime.fromisoformat(p["evaluate_as_of"]), user, db)
    return {"import": imported, "evaluation": evaluated, "fixture": "SYNTHETIC"}
