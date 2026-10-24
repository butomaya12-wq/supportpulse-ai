"""Independent and coupled tests for safe autonomous *synthetic* incident repair."""
from pathlib import Path
import copy
import time

import pytest
import yaml
from fastapi.testclient import TestClient

from app import repair_drill
from oncall import agent
from oncall.main import app as oncall_app

SECRET = "test-repair-secret-" + "7" * 50
FIRING = {
    "status": "firing",
    "alerts": [{
        "status": "firing",
        "labels": {
            "alertname": agent.ALERT_NAME,
            "project": "supportpulse-ai",
            "stage": "synthetic-only",
            "user_impact": "critical-overview-read",
            "__alert_rule_uid__": agent.ALERT_UID,
        },
        "fingerprint": "9999aabbccddeeff",
        "startsAt": "2026-10-24T16:00:00Z",
    }],
}


@pytest.fixture
def repair_client(ctx, monkeypatch):
    c, Session = ctx
    monkeypatch.setenv("SP_MODE", "synthetic_local")
    monkeypatch.setenv("SP_REPAIR_DRILL_ENABLED", "1")
    monkeypatch.setenv("SP_REPAIR_TOKEN", SECRET)
    monkeypatch.setattr(repair_drill, "_EXPIRY", 0.0)
    monkeypatch.setattr(repair_drill, "_REVISION", 0)
    yield c, Session
    monkeypatch.setattr(repair_drill, "_EXPIRY", 0.0)


def hdr(action):
    return {"Authorization": "Bearer " + SECRET,
            "X-SupportPulse-Repair-Drill": action}


def test_arming_requires_secret_and_intent_and_does_not_touch_business_db(repair_client, supervisor):
    c, Session = repair_client
    from sqlalchemy import select, func
    from app.models import Audit, Source, Commitment, Finding, CorrectiveAction
    models = (Audit, Source, Commitment, Finding, CorrectiveAction)
    with Session() as db:
        before = [db.scalar(select(func.count()).select_from(x)) for x in models]
    assert c.post("/api/v1/demo/repair-drill/arm").status_code == 401
    assert c.post("/api/v1/demo/repair-drill/arm", headers=hdr("repair")).status_code == 401
    assert c.get("/api/v1/demo/repair-drill/state", headers=hdr("inspect")).json()["state"] == "READY"
    result = c.post("/api/v1/demo/repair-drill/arm", headers=hdr("arm"))
    assert result.status_code == 200
    revision = result.json()["revision"]
    assert result.json()["max_duration_seconds"] == 600
    assert c.post("/api/v1/demo/repair-drill/arm", headers=hdr("arm")).status_code == 409
    assert c.get("/api/v1/overview", headers=supervisor).status_code == 503
    assert c.get("/health").status_code == 200
    assert c.post("/api/v1/demo/repair-drill/repair?expected_revision=999",
                  headers=hdr("repair")).status_code == 409
    assert c.get("/api/v1/overview", headers=supervisor).status_code == 503
    applied = c.post(f"/api/v1/demo/repair-drill/repair?expected_revision={revision}",
                     headers=hdr("repair"))
    assert applied.status_code == 200
    assert applied.json()["repair_applied"] is True
    assert c.get("/api/v1/overview", headers=supervisor).status_code == 200
    assert c.post(f"/api/v1/demo/repair-drill/repair?expected_revision={revision}",
                  headers=hdr("repair")).status_code == 409
    with Session() as db:
        assert [db.scalar(select(func.count()).select_from(x)) for x in models] == before


def test_broken_gate_expires_and_is_forbidden_without_opt_in(repair_client, supervisor, monkeypatch):
    c, _ = repair_client
    assert c.post("/api/v1/demo/repair-drill/arm", headers=hdr("arm")).status_code == 200
    monkeypatch.setattr(repair_drill, "_EXPIRY", time.monotonic() - 1)
    assert c.get("/api/v1/overview", headers=supervisor).status_code == 200
    assert c.get("/api/v1/demo/repair-drill/state", headers=hdr("inspect")).json()["state"] == "READY"
    monkeypatch.setenv("SP_REPAIR_DRILL_ENABLED", "0")
    assert c.post("/api/v1/demo/repair-drill/arm", headers=hdr("arm")).status_code == 404
    assert c.get("/api/v1/overview", headers=supervisor).status_code == 200


def test_agent_fixes_only_verified_latch_and_records_before_after(repair_client, monkeypatch, tmp_path, supervisor):
    c, _ = repair_client
    monkeypatch.setenv("SP_ONCALL_DB", str(tmp_path / "oncall.sqlite3"))
    monkeypatch.setenv("SP_ONCALL_WEBHOOK_TOKEN", SECRET)
    monkeypatch.setenv("SP_SUPERVISOR_TOKEN", "dev-only-supervisor-token")
    agent.init_store()

    def bounded_internal(path, intent, method="GET"):
        if path == "/api/v1/demo/repair-drill/state" and intent == "inspect":
            response = c.get(path, headers=hdr("inspect"))
        elif path.startswith("/api/v1/demo/repair-drill/repair?expected_revision=") and intent == "repair":
            response = c.post(path, headers=hdr("repair"))
        else:
            pytest.fail("Unallowlisted internal repair call")
        return response.json() if response.status_code == 200 else None

    monkeypatch.setattr(agent, "_repair_request", bounded_internal)
    monkeypatch.setattr(agent, "_http_probe",
                        lambda path, authenticated=False: c.get(
                            path, headers=supervisor if authenticated else {}).status_code)
    monkeypatch.setattr(agent, "diagnose", lambda: (
        c.get("/health").status_code, c.get("/api/v1/overview", headers=supervisor).status_code))

    assert c.post("/api/v1/demo/repair-drill/arm", headers=hdr("arm")).status_code == 200
    assert c.get("/api/v1/overview", headers=supervisor).status_code == 503
    with TestClient(oncall_app) as oc:
        response = oc.post("/webhook", json=FIRING, headers={"Authorization": "Bearer " + SECRET})
        assert response.status_code == 202, response.text
        result = response.json()
        assert result["outcome"] == "AUTO_REPAIRED_SYNTHETIC", result
        assert result["action"] == "REPAIR_SYNTHETIC_OVERVIEW_GATE"
        assert result["post_repair_http"] == 200
        assert result["repair_revision"] == 1
        assert result["verified_recovery"] is False
        assert c.get("/api/v1/overview", headers=supervisor).status_code == 200
        replay = oc.post("/webhook", json=FIRING, headers={"Authorization": "Bearer " + SECRET}).json()
        assert replay["duplicate"] is True
        assert replay["action"] == "NO_ACTION_REPLAY"
        resolved = copy.deepcopy(FIRING)
        resolved["status"] = "resolved"
        resolved["alerts"][0]["status"] = "resolved"
        r = oc.post("/webhook", json=resolved, headers={"Authorization": "Bearer " + SECRET}).json()
        assert r["outcome"] == "VERIFIED_RESOLVED"
        assert r["verified_recovery"] is True
        records = oc.get("/events", headers={"Authorization": "Bearer " + SECRET}).json()["events"]
        assert len(records) == 2
        assert records[1]["overview_http"] == 503
        assert records[1]["post_repair_http"] == 200


def test_unverified_503_never_triggers_repair(monkeypatch, tmp_path):
    monkeypatch.setenv("SP_MODE", "synthetic_local")
    monkeypatch.setenv("SP_REPAIR_DRILL_ENABLED", "1")
    monkeypatch.setenv("SP_REPAIR_TOKEN", SECRET)
    monkeypatch.setenv("SP_ONCALL_DB", str(tmp_path / "journal.sqlite3"))
    agent.init_store()
    monkeypatch.setattr(agent, "diagnose", lambda: (200, 503))
    monkeypatch.setattr(agent, "_repair_request", lambda path, intent, method="GET": {
        "data_mode": "SYNTHETIC_ONLY", "state": "READY", "revision": 7,
    } if intent == "inspect" else pytest.fail("Agent attempted a repair without BROKEN evidence"))
    result = agent.consume(FIRING)
    assert result["outcome"] == "INVESTIGATE_OVERVIEW_FAILURE"
    assert result["action"] == "TWO_READ_ONLY_PROBES"


def test_repair_overlay_is_optional_and_secret_not_literal():
    root = Path(__file__).resolve().parents[1]
    overlay = yaml.safe_load((root / "compose.repair.yaml").read_text())
    for service in ("web", "oncall"):
        env = overlay["services"][service]["environment"]
        assert env["SP_REPAIR_DRILL_ENABLED"] == "1"
        assert "SP_REPAIR_TOKEN:?" in env["SP_REPAIR_TOKEN"]
    assert "db" not in overlay["services"]
