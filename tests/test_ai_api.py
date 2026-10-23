"""Read-only AI candidate endpoint acceptance tests; no external model traffic."""
from sqlalchemy import select, func
from app.models import Commitment
from app.ai_extract import RawCandidate

PATH = "/api/v1/ai/proposals"
INPUT = {"source_id": "demo-instagram", "conversation_id": "demo-lead-001"}


def test_proposals_are_read_only_and_do_not_approve_or_accuse(ctx, supervisor, initial, monkeypatch):
    c, Session = ctx
    monkeypatch.setenv("SP_AI_PROVIDER", "rules")
    assert c.post("/api/v1/imports", headers=supervisor, json=initial["import"]).status_code == 200
    response = c.post(PATH, headers=supervisor, json=INPUT)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["provider"] == "RULE_BASELINE_NOT_AI"
    assert data["review_required"] is True
    assert data["external_model_invoked"] is False
    assert len(data["proposals"]) == 1
    proposed = data["proposals"][0]
    assert proposed["status"] == "PROPOSED_NOT_APPROVED"
    assert proposed["basis_external_id"] == "msg-002"
    assert proposed["evidence_quote"] == "Отправлю расчёт сегодня до 16:00."
    assert proposed["due_at"] == "2026-10-22T16:00:00+03:00"
    assert proposed["confidence"] is None
    assert proposed["financial_impact"] is None
    with Session() as db:
        assert db.scalar(select(func.count()).select_from(Commitment)) == 0
    assert c.get("/api/v1/findings", headers=supervisor).json()["data"] == []
    # Only an explicit human-approved call to the preexisting endpoint can persist.
    approved = c.post("/api/v1/commitments", headers=supervisor, json={
        "source_id": proposed["source_id"],
        "basis_external_id": proposed["basis_external_id"],
        "due_at": proposed["due_at"],
        "action_type": proposed["action_type"],
    })
    assert approved.status_code == 200
    assert approved.json()["created"] is True
    with Session() as db:
        assert db.scalar(select(func.count()).select_from(Commitment)) == 1
    # Repeated proposal or explicit approval is idempotent.
    assert c.post(PATH, headers=supervisor, json=INPUT).status_code == 200
    assert c.post("/api/v1/commitments", headers=supervisor, json={
        "source_id": proposed["source_id"],
        "basis_external_id": proposed["basis_external_id"],
        "due_at": proposed["due_at"],
        "action_type": proposed["action_type"],
    }).json()["created"] is False


def test_role_scoping_missing_source_and_degraded_source(ctx, supervisor, manager, initial, monkeypatch):
    c, Session = ctx
    monkeypatch.setenv("SP_AI_PROVIDER", "rules")
    assert c.post(PATH, json=INPUT).status_code == 401
    assert c.post(PATH, headers=manager, json=INPUT).status_code == 403
    assert c.post(PATH, headers=supervisor, json=INPUT).status_code == 404
    initial["import"]["healthy"] = False
    assert c.post("/api/v1/imports", headers=supervisor, json=initial["import"]).status_code == 200
    data = c.post(PATH, headers=supervisor, json=INPUT).json()
    assert data["proposals"] == []
    assert data["abstentions"] == [{"reason": "INSUFFICIENT_SOURCE_COVERAGE"}]
    with Session() as db:
        assert db.scalar(select(func.count()).select_from(Commitment)) == 0


def test_unknown_manager_message_and_provider_disabled(ctx, supervisor, initial, monkeypatch):
    c, _ = ctx
    monkeypatch.setenv("SP_AI_PROVIDER", "off")
    c.post("/api/v1/imports", headers=supervisor, json=initial["import"])
    disabled = c.post(PATH, headers=supervisor, json=INPUT).json()
    assert disabled["proposals"] == []
    assert disabled["abstentions"][0]["reason"] == "PROVIDER_DISABLED"
    none = c.post(PATH, headers=supervisor, json={
        "source_id": "demo-instagram", "conversation_id": "another-conversation"}).json()
    assert none["proposals"] == []
    assert none["abstentions"] == [{"reason": "NO_MANAGER_MESSAGES"}]


def test_model_adaptor_mocked_and_validated_against_immutable_event(ctx, supervisor, initial, monkeypatch):
    from app import ai_extract
    c, _ = ctx
    monkeypatch.setenv("SP_AI_PROVIDER", "openai")
    c.post("/api/v1/imports", headers=supervisor, json=initial["import"])
    monkeypatch.setattr(ai_extract, "_openai_candidate", lambda msg, at:
        RawCandidate(is_promise=True, quote=msg, due_at="2026-10-22T17:00:00+03:00"))
    invalid = c.post(PATH, headers=supervisor, json=INPUT).json()
    assert invalid["proposals"] == []
    assert invalid["abstentions"][0]["reason"] == "NO_VERIFIABLE_EXPLICIT_PROMISE"
    monkeypatch.setattr(ai_extract, "_openai_candidate", lambda msg, at:
        RawCandidate(is_promise=True, quote=msg, due_at="2026-10-22T16:00:00+03:00"))
    valid = c.post(PATH, headers=supervisor, json=INPUT).json()
    assert valid["provider"] == "OPENAI"
    assert len(valid["proposals"]) == 1
    assert valid["review_required"] is True


def test_large_or_ambiguous_message_abstains(ctx, supervisor, initial, monkeypatch):
    c, _ = ctx
    monkeypatch.setenv("SP_AI_PROVIDER", "rules")
    events = initial["import"]["events"]
    events[1]["message"] = "Отправлю расчёт сегодня до 16:00." + "x" * 2100
    c.post("/api/v1/imports", headers=supervisor, json=initial["import"])
    data = c.post(PATH, headers=supervisor, json=INPUT).json()
    assert data["proposals"] == []
    assert data["abstentions"][0]["reason"] == "MESSAGE_TOO_LONG"
