"""Telemetry contract: trace ID, minimal cardinality, never export raw user input."""
import json
import logging
import re

from app import telemetry as t

SECRET = "SENSITIVE_EVENT_TEXT_DO_NOT_EXPORT"


class Capturer(logging.Handler):
    def __init__(self):
        super().__init__()
        self.setFormatter(t.RedactedJsonFormatter())
        self.rows = []

    def emit(self, record):
        self.rows.append(json.loads(self.format(record)))


def test_header_and_correlated_safe_operations(ctx, supervisor, initial, monkeypatch):
    client, _ = ctx
    monkeypatch.delenv("SP_TELEMETRY_ENABLED", raising=False)
    assert t._started is False
    capture = Capturer()
    t.logger.addHandler(capture)
    try:
        initial["import"]["events"][1]["message"] += SECRET
        response = client.post("/api/v1/imports", headers=supervisor,
                               json=initial["import"])
        assert response.status_code == 200, response.text
        trace_id = response.headers["x-trace-id"]
        assert re.fullmatch(r"[0-9a-f]{32}", trace_id)
        result = client.get("/api/v1/findings",
                            headers=supervisor,
                            params={"search": SECRET})
        assert result.status_code == 200
        assert re.fullmatch(r"[0-9a-f]{32}", result.headers["x-trace-id"])
        audit = [x for x in capture.rows if x["event"] == "business.audit_queued"]
        finished = [x for x in capture.rows if x["event"] == "http.completed"]
        assert audit and finished
        assert audit[0]["trace_id"] == trace_id
        assert any(x["trace_id"] == trace_id and x["route"] == "/api/v1/imports"
                   for x in finished)
        flattened = json.dumps(capture.rows)
        assert SECRET not in flattened
        assert "dev-only-supervisor-token" not in flattened
        assert "demo-manager-001" not in flattened
        assert "demo-lead-001" not in flattened
        assert all("?" not in x["route"] for x in capture.rows)
    finally:
        t.logger.removeHandler(capture)


def test_telemetry_logs_do_not_inherit_arbitrary_record_properties():
    record = logging.LogRecord("supportpulse.ops", logging.INFO, "unsafe.py", 4,
                               "user says: " + SECRET, (), None)
    record.trace_id = "ff" * 16
    record.payload = SECRET
    record.authorization = "Bearer DEV_CREDS"
    record.message_text = SECRET
    sanitized = t.RedactedJsonFormatter().format(record)
    data = json.loads(sanitized)
    assert data["event"] == "ops.event"
    assert data["trace_id"] == "ff" * 16
    assert SECRET not in sanitized
    assert "DEV_CREDS" not in sanitized


def test_invalid_trace_id_is_not_forwarded():
    record = logging.LogRecord("supportpulse.ops", logging.INFO, "safe.py", 4,
                               "http.completed", (), None)
    record.trace_id = SECRET
    result = json.loads(t.RedactedJsonFormatter().format(record))
    assert result["trace_id"] == "none"


def test_bad_route_and_error_status_have_safe_http_log(ctx, supervisor):
    c, _ = ctx
    capture = Capturer()
    t.logger.addHandler(capture)
    try:
        r = c.get("/api/v1/findings/999", headers=supervisor)
        assert r.status_code == 404
        assert re.fullmatch(r"[a-f0-9]{32}", r.headers["x-trace-id"])
        rows = [row for row in capture.rows if row["event"] == "http.completed"]
        assert len(rows) == 1
        assert rows[0]["route"] == "/api/v1/findings/{finding_id}"
        assert rows[0]["status_class"] == "4xx"
        assert "999" not in rows[0]["route"]
    finally:
        t.logger.removeHandler(capture)


def test_operation_transition_is_low_cardinality(monkeypatch):
    counter_calls = []
    class DummyCounter:
        def add(self, value, attributes):
            counter_calls.append((value, attributes))
    monkeypatch.setattr(t, "_transition_counter", DummyCounter())
    t.mark_audit_queued("ACTION_CLOSED")
    t.mark_audit_queued("ID-" + SECRET)
    assert counter_calls == [
        (1, {"transition": "ACTION_CLOSED"}),
        (1, {"transition": "OTHER"}),
    ]
