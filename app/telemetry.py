"""Bounded, privacy-preserving OpenTelemetry signals for the SYNTHETIC demo.

Only low-cardinality route and transition classes are exported. Never export request
bodies, headers, authentication, source IDs, external IDs or human/LLM message text.
Disabled by default to preserve previous local application behavior.
"""
import json
import logging
from contextvars import ContextVar
import os
import re
import sys
import time
from uuid import uuid4

from fastapi import Request
from opentelemetry import metrics, trace
from opentelemetry.trace import Status, StatusCode
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

logger = logging.getLogger("supportpulse.ops")
logger.propagate = False
logger.setLevel(logging.INFO)

_SAFE_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"}
_SAFE_TRANSITIONS = {
    "IMPORT", "HUMAN_APPROVED", "EVALUATED", "RE_EVALUATED",
    "HUMAN_REVIEW", "ASSIGNED", "PROVIDER_PROOF_VERIFIED", "ACTION_CLOSED",
}
_started = False
_counter = None
_duration = None
_blocked = None
_transition_counter = None
# Starlette/AnyIO propagates this context into sync endpoint worker threads.
_request_trace_id: ContextVar[str | None] = ContextVar("sp_request_trace_id", default=None)


class RedactedJsonFormatter(logging.Formatter):
    """Do not serialize caller-added record attributes or exception traceback."""
    def format(self, record: logging.LogRecord) -> str:
        trace_id = getattr(record, "trace_id", "")
        if not isinstance(trace_id, str) or not re.fullmatch(r"[0-9a-f]{32}", trace_id):
            trace_id = "none"
        return json.dumps({
            "event": str(record.msg) if record.msg in {"http.completed", "business.audit_queued"} else "ops.event",
            "trace_id": trace_id,
            "route": getattr(record, "route", "none"),
            "method": getattr(record, "method", "none"),
            "status_class": getattr(record, "status_class", "none"),
            "transition": getattr(record, "transition", "none"),
        }, ensure_ascii=True, separators=(",", ":"))


def setup_telemetry() -> None:
    """Wire traces, metrics AND application logs to an opt-in OTLP/HTTP collector."""
    global _started, _counter, _duration, _blocked, _transition_counter
    if _started or os.getenv("SP_TELEMETRY_ENABLED") != "1":
        return
    # This service cannot be used with real customer data and must not export secrets.
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-lgtm:4318").rstrip("/")
    if not endpoint.startswith(("http://", "https://")):
        raise RuntimeError("OTLP endpoint requires http(s)")
    resource = Resource.create({
        "service.name": "supportpulse-ai",
        "service.version": "0.5.0",
        "deployment.environment": "synthetic_local",
    })
    traces = TracerProvider(resource=resource)
    traces.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint + "/v1/traces", timeout=4)))
    trace.set_tracer_provider(traces)
    reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=endpoint + "/v1/metrics", timeout=4),
        export_interval_millis=5000,
    )
    metrics.set_meter_provider(MeterProvider(metric_readers=[reader], resource=resource))
    meter = metrics.get_meter("supportpulse.ops")
    _counter = meter.create_counter("supportpulse_http_requests", unit="1")
    _duration = meter.create_histogram("supportpulse_http_duration_ms", unit="ms")
    _blocked = meter.create_counter("supportpulse_verification_rejected", unit="1")
    _transition_counter = meter.create_counter("supportpulse_business_audit_attempts", unit="1")
    logs = LoggerProvider(resource=resource)
    logs.add_log_record_processor(BatchLogRecordProcessor(
        OTLPLogExporter(endpoint=endpoint + "/v1/logs", timeout=4)))
    logger.addHandler(LoggingHandler(level=logging.INFO, logger_provider=logs))
    _started = True


def _route_template(request: Request) -> str:
    """FastAPI sets route path template after routing; no raw URL/query or customer IDs."""
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    if isinstance(path, str) and path.startswith("/") and len(path) <= 110:
        # The route is a declared template, never an untrusted request path.
        return path
    return "unmatched"


def _trace_id() -> str:
    context = trace.get_current_span().get_span_context()
    if context.is_valid:
        return f"{context.trace_id:032x}"
    return _request_trace_id.get() or uuid4().hex


async def instrument_request(request: Request, call_next):
    """One span, log and count per HTTP request; no raw payload export, even on errors."""
    tracer = trace.get_tracer("supportpulse.http")
    method = request.method if request.method in _SAFE_METHODS else "OTHER"
    start = time.perf_counter()
    with tracer.start_as_current_span("http.request") as span:
        # Keep one stable ID even with OTLP disabled/no-op tracer. This also
        # propagates safely across FastAPI worker-thread boundaries.
        token = _request_trace_id.set(_trace_id())
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        except Exception:
            # Don't write exceptions to exported spans/logs; they can include PII.
            if span.is_recording():
                span.set_status(Status(StatusCode.ERROR, "HTTP 5xx"))
            raise
        finally:
            route = _route_template(request)
            status_class = f"{status // 100}xx"
            elapsed = (time.perf_counter() - start) * 1000
            current_trace = _trace_id()
            if span.is_recording():
                span.update_name(f"{method} {route}")
                span.set_attribute("http.request.method", method)
                span.set_attribute("http.route", route)
                span.set_attribute("http.response.status_code", status)
                if status >= 500:
                    span.set_status(Status(StatusCode.ERROR, "HTTP 5xx"))
            attributes = {"http.route": route, "http.request.method": method,
                          "http.response.status_class": status_class}
            if _counter is not None:
                _counter.add(1, attributes)
                _duration.record(elapsed, attributes)
                if route == "/api/v1/actions/{action_id}/verify" and status == 409:
                    _blocked.add(1, {"http.route": route, "outcome": "blocked"})
            # Only safe low-cardinality attributes; exclude event/source/actor IDs.
            logger.info("http.completed", extra={
                "trace_id": current_trace, "route": route,
                "method": method, "status_class": status_class,
            })
            if status != 500 and "response" in locals():
                response.headers["X-Trace-Id"] = current_trace
            _request_trace_id.reset(token)


def mark_audit_queued(action: str) -> None:
    """Mark attempt only: DB may still roll back; do not claim business completion."""
    safe_action = action if action in _SAFE_TRANSITIONS else "OTHER"
    active_span = trace.get_current_span()
    if active_span.is_recording():
        active_span.add_event("business.audit_queued", {"business.transition": safe_action})
    if _transition_counter is not None:
        _transition_counter.add(1, {"transition": safe_action})
    logger.info("business.audit_queued", extra={
        "trace_id": _trace_id(), "transition": safe_action,
    })


def add_stdout_safe_log() -> None:
    """Attach exactly one scrubbed JSON stdout handler, not a generic root logger."""
    if any(getattr(handler, "_sp_safe_stdout", False) for handler in logger.handlers):
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(RedactedJsonFormatter())
    handler._sp_safe_stdout = True
    logger.addHandler(handler)
