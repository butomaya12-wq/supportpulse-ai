"""Alert drill does not affect real views, write to DB, or leak raw headers."""
import re
import yaml

from app import telemetry
from app.fault_drill import synthetic_overview_failure_enabled
from pathlib import Path


DRILL = {"X-SupportPulse-Drill": "overview-503"}


def test_fault_drill_disabled_by_default_and_never_disables_real_dashboard(ctx, supervisor, monkeypatch):
    client, _ = ctx
    monkeypatch.delenv("SP_FAULT_DRILL_ENABLED", raising=False)
    original = client.get("/api/v1/overview", headers=supervisor)
    injected = client.get("/api/v1/overview", headers={**supervisor, **DRILL})
    assert original.status_code == 200
    assert injected.status_code == 200
    assert original.json()["data_mode"] == "SYNTHETIC_ONLY"


def test_fault_drill_is_supervisor_only_and_requires_exact_header(ctx, supervisor, manager, monkeypatch):
    c, _ = ctx
    monkeypatch.setenv("SP_FAULT_DRILL_ENABLED", "1")
    assert c.get("/api/v1/overview", headers=DRILL).status_code == 401
    assert c.get("/api/v1/overview", headers={**manager, **DRILL}).status_code == 403
    assert c.get("/api/v1/overview", headers={**supervisor, "X-SupportPulse-Drill": "wrong"}).status_code == 200
    assert c.get("/api/v1/overview", headers=supervisor).status_code == 200


def test_exact_opt_in_returns_observable_503_but_no_database_mutation(ctx, supervisor, monkeypatch):
    c, Session = ctx
    from sqlalchemy import select, func
    from app.models import Audit, Source, Commitment, Finding, CorrectiveAction

    monkeypatch.setenv("SP_MODE", "synthetic_local")
    monkeypatch.setenv("SP_FAULT_DRILL_ENABLED", "1")
    before = {}
    with Session() as db:
        for model in [Audit, Source, Commitment, Finding, CorrectiveAction]:
            before[model.__tablename__] = db.scalar(select(func.count()).select_from(model))
    class MeterStub:
        def __init__(self):
            self.counts = []
        def add(self, amount, attrs):
            self.counts.append((amount, attrs))
    stub = MeterStub()
    class HistogramStub:
        def __init__(self):
            self.samples = []
        def record(self, amount, attrs):
            self.samples.append((amount, attrs))
    histogram = HistogramStub()
    monkeypatch.setattr(telemetry, "_counter", stub)
    monkeypatch.setattr(telemetry, "_duration", histogram)
    r = c.get("/api/v1/overview", headers={**supervisor, **DRILL})
    assert r.status_code == 503
    assert "SYNTHETIC_ONLY" in r.json()["detail"]
    assert re.fullmatch(r"[0-9a-f]{32}", r.headers["x-trace-id"])
    assert (1, {
        "http.route": "/api/v1/overview",
        "http.request.method": "GET",
        "http.response.status_class": "5xx",
    }) in stub.counts
    assert histogram.samples and histogram.samples[0][0] >= 0
    assert c.get("/api/v1/overview", headers=supervisor).status_code == 200
    with Session() as db:
        for model in [Audit, Source, Commitment, Finding, CorrectiveAction]:
            assert db.scalar(select(func.count()).select_from(model)) == before[model.__tablename__]


def test_not_available_outside_synthetic_mode(ctx, supervisor, monkeypatch):
    client, _ = ctx
    monkeypatch.setenv("SP_MODE", "production")
    monkeypatch.setenv("SP_FAULT_DRILL_ENABLED", "1")
    assert client.get("/api/v1/overview", headers={**supervisor, **DRILL}).status_code == 200


def test_file_provisioned_rule_has_meaningful_signal_not_token_or_user_id():
    root = Path(__file__).resolve().parents[1]
    rule_file = root / "ops/grafana/alerting/overview-5xx.yaml"
    data = yaml.safe_load(rule_file.read_text())
    rule = data["groups"][0]["rules"][0]
    assert rule["uid"] == "sp_overview_5xx_v1"
    assert rule["isPaused"] is False
    assert rule["condition"] == "C"
    assert rule["noDataState"] == "OK"
    assert rule["for"] == "0s"
    query = rule["data"][0]
    expr = query["model"]["expr"]
    assert query["datasourceUid"] == "prometheus"
    assert "supportpulse_http_requests_total" in expr
    assert 'http_route="/api/v1/overview"' in expr
    assert 'http_request_method="GET"' in expr
    assert 'http_response_status_class="5xx"' in expr
    assert "[2m]" in expr
    assert "increase(" in expr
    assert " or vector(0)" in expr
    assert len(data["groups"][0]["rules"]) == 1
    overlay = (root / "compose.alerts.yaml").read_text()
    assert "SP_FAULT_DRILL_ENABLED" in overlay
    assert "overview-5xx.yaml" in overlay
    assert "127.0.0.1:18080" not in overlay
    for forbidden in ["Authorization", "Bearer", "customer_id", "source_id", "actor_id", "conversation_id", "message", "token"]:
        assert forbidden.lower() not in expr.lower()
