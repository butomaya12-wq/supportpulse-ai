"""Safety and idempotency acceptance for bounded Grafana on-call service."""
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from oncall import agent
from oncall.main import app

TOKEN = "test-only-strong-secret-" + "9" * 48
HEADERS = {"Authorization": "Bearer " + TOKEN}
ALERT = {
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
        "fingerprint": "1234567890abcdef",
        "startsAt": "2026-10-24T13:41:00Z",
        "annotations": {"message": "NOT_FOR_LOGS_PRIVATE_TEST"},
    }],
    "title": "UNTRUSTED_PAYLOAD",
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("SP_MODE", "synthetic_local")
    monkeypatch.setenv("SP_ONCALL_WEBHOOK_TOKEN", TOKEN)
    monkeypatch.setenv("SP_SUPERVISOR_TOKEN", "isolated-e2e-supervisor")
    monkeypatch.setenv("SP_ONCALL_DB", str(tmp_path / "oncall.sqlite3"))
    monkeypatch.setenv("SP_ONCALL_TARGET", "http://web:8000")
    with TestClient(app) as test:
        yield test


def test_auth_required_for_webhook_and_audit(client):
    assert client.post("/webhook", json=ALERT).status_code == 401
    assert client.post("/webhook", headers={"Authorization": "Bearer wrong"}, json=ALERT).status_code == 401
    assert client.get("/events").status_code == 401
    assert client.get("/health").json()["data_mode"] == "SYNTHETIC_ONLY"


def test_firing_real_webhook_diagnoses_but_cannot_claim_recovery(client, monkeypatch):
    calls = []
    def probe():
        calls.append("read-only")
        return (200, 200)
    monkeypatch.setattr(agent, "diagnose", probe)
    one = client.post("/webhook", json=ALERT, headers=HEADERS)
    assert one.status_code == 202, one.text
    result = one.json()
    assert result["accepted"] and not result["duplicate"]
    assert result["outcome"] == "ALERT_ACTIVE_PROBE_HEALTHY"
    assert result["verified_recovery"] is False
    assert result["action"] == "TWO_READ_ONLY_PROBES"
    again = client.post("/webhook", json=ALERT, headers=HEADERS)
    assert again.status_code == 202
    assert again.json()["duplicate"] is True
    assert again.json()["action"] == "NO_ACTION_REPLAY"
    assert calls == ["read-only"]
    history = client.get("/events", headers=HEADERS).json()["events"]
    assert len(history) == 1
    assert history[0]["alert_status"] == "firing"
    assert history[0]["verified_recovery"] == 0
    assert "NOT_FOR_LOGS_PRIVATE_TEST" not in str(history)
    assert "1234567890abcdef" not in str(history)
    assert TOKEN not in str(history)


def test_recovery_requires_resolved_notification_and_both_successful_probes(client, monkeypatch):
    inputs = [(200, 503), (200, 200)]
    monkeypatch.setattr(agent, "diagnose", lambda: inputs.pop(0))
    r = client.post("/webhook", json=ALERT, headers=HEADERS)
    assert r.json()["outcome"] == "INVESTIGATE_OVERVIEW_FAILURE"
    assert not r.json()["verified_recovery"]
    resolved = {**ALERT, "status": "resolved", "alerts": [{**ALERT["alerts"][0], "status": "resolved"}]}
    answer = client.post("/webhook", json=resolved, headers=HEADERS)
    assert answer.status_code == 202
    assert answer.json()["outcome"] == "VERIFIED_RESOLVED"
    assert answer.json()["verified_recovery"] is True
    assert len(client.get("/events", headers=HEADERS).json()["events"]) == 2


def test_bad_recovery_does_not_lie(client, monkeypatch):
    monkeypatch.setattr(agent, "diagnose", lambda: (200, 503))
    resolved = {**ALERT, "status": "resolved", "alerts": [{**ALERT["alerts"][0], "status": "resolved"}]}
    output = client.post("/webhook", headers=HEADERS, json=resolved).json()
    assert output["outcome"] == "RESOLUTION_UNVERIFIED"
    assert output["verified_recovery"] is False


@pytest.mark.parametrize("mutation", [
    lambda x: x.update(status="nope"),
    lambda x: x.update(alerts=[]),
    lambda x: x["alerts"][0]["labels"].update(project="other"),
    lambda x: x["alerts"][0]["labels"].update(alertname="Other alert"),
    lambda x: x["alerts"][0]["labels"].update(stage="production"),
    lambda x: x["alerts"][0]["labels"].update(__alert_rule_uid__="wrong"),
    lambda x: x["alerts"][0].update(fingerprint="not-hex"),
    lambda x: x["alerts"][0].update(startsAt="tomorrow"),
    lambda x: x["alerts"][0].update(status="resolved"),
])
def test_forged_unknown_invalid_alert_fails_closed(client, monkeypatch, mutation):
    import copy
    monkeypatch.setattr(agent, "diagnose", lambda: pytest.fail("untrusted notification invoked probe"))
    data = copy.deepcopy(ALERT)
    mutation(data)
    r = client.post("/webhook", headers=HEADERS, json=data)
    assert r.status_code == 422
    assert client.get("/events", headers=HEADERS).json()["events"] == []


def test_wrong_content_type_and_oversized_payload_blocked(client):
    assert client.post("/webhook", headers={**HEADERS, "Content-Type": "text/plain"}, content="hi").status_code == 415
    assert client.post("/webhook", headers=HEADERS, json={"garbage": "x" * 20000}).status_code == 413
    assert client.post("/webhook", headers=HEADERS, content=b"{", ).status_code in {415, 422}


def test_target_allowlist_disallows_external_network(monkeypatch):
    for value in [
        "https://example.com",
        "http://169.254.169.254:80",
        "http://web:9999",
        "http://web:8000/path",
        "http://guest@web:8000",
    ]:
        monkeypatch.setenv("SP_ONCALL_TARGET", value)
        with pytest.raises(RuntimeError):
            agent._target_url("/health")


def test_persistence_and_deduplication_after_new_client_lifespan(client, monkeypatch):
    monkeypatch.setattr(agent, "diagnose", lambda: (200, 200))
    assert client.post("/webhook", headers=HEADERS, json=ALERT).json()["duplicate"] is False
    with TestClient(app) as restarted:
        assert restarted.post("/webhook", headers=HEADERS, json=ALERT).json()["duplicate"] is True
        assert len(restarted.get("/events", headers=HEADERS).json()["events"]) == 1


def test_provisioned_receiver_rule_and_compose_contract():
    root = Path(__file__).resolve().parents[1]
    contact = yaml.safe_load((root / "ops/grafana/alerting/oncall-contact.yaml").read_text())
    r = contact["contactPoints"][0]["receivers"][0]
    assert r["type"] == "webhook"
    assert r["settings"]["url"] == "http://oncall:8081/webhook"
    assert r["settings"]["authorization_scheme"] == "Bearer"
    assert r["settings"]["authorization_credentials"] == "$SP_ONCALL_WEBHOOK_TOKEN"
    assert r["disableResolveMessage"] is False
    rule = yaml.safe_load((root / "ops/grafana/alerting/overview-5xx-oncall.yaml").read_text())
    n = rule["groups"][0]["rules"][0]
    assert n["uid"] == agent.ALERT_UID
    assert n["notification_settings"]["receiver"] == contact["contactPoints"][0]["name"]
    assert n["notification_settings"]["group_wait"] == "0s"
    original = yaml.safe_load((root / "ops/grafana/alerting/overview-5xx.yaml").read_text())
    assert "notification_settings" not in original["groups"][0]["rules"][0]
    overlay = (root / "compose.oncall.yaml").read_text()
    assert "SP_ONCALL_WEBHOOK_TOKEN: ${SP_ONCALL_WEBHOOK_TOKEN:?" in overlay
    assert "127.0.0.1:18081:8081" in overlay
    assert "postgres_data" not in overlay
