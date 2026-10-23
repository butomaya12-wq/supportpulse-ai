# SupportPulse AI — Observability (iteration 005)

**Status:** instrumentation coded for a **synthetic-only**, local environment. Do not assert course 2/2 observability points until you have screenshots of real logs, metrics, and traces stored in Grafana with matching trace IDs.

## What is recorded

- **HTTP request span:** `http.request`, renamed to `GET /api/v1/findings/{finding_id}` etc. Only the declared route template, HTTP method, status code. Never raw URLs/query strings, headers, body, account/lead/source identifiers or message text.
- **Structured JSON log:** `http.completed` with `trace_id`, route template, HTTP method and status class. Another log `business.audit_queued` marks that an audit event was **queued** (not a claim that the DB commit succeeded).
- **Business span event:** `business.audit_queued` on the active HTTP trace. Uses only a static transition type (`HUMAN_APPROVED`, `HUMAN_REVIEW`, `ASSIGNED`, `ACTION_CLOSED`, etc.).
- **Metrics:** `supportpulse_http_requests` (count), `supportpulse_http_duration_ms` (latency histogram), `supportpulse_verification_rejected` (409 safety gate), `supportpulse_business_audit_attempts` (attempted transition counters). Labels contain only route templates/status class and allowlisted transition type. Not per-user/case identifiers.
- **Cross-signal correlation:** each HTTP response contains `X-Trace-Id`. The matching log and OpenTelemetry span share this 32-hex-character trace ID when the exporter is enabled. Operations from different HTTP requests have different traces; end-to-end multi-request journey correlation is still limited.

`supportpulse_verification_rejected` measures safe intentional rejection of invalid actions. **This is not a count of broken user journeys and must not be used directly as an outage alert.** A separate alert must target a reproducible **actual user-impact failure**, e.g. 5xx on an essential workflow.

## Safety and default

- `SP_TELEMETRY_ENABLED` is **off** in the normal `compose.yaml`; when off, no OpenTelemetry exporters or background export threads start. Redacted JSON operational logs are still written to stdout.
- The optional `compose.telemetry.yaml` overlay uses `grafana/otel-lgtm:0.37.0`, a **development-only** distribution of Grafana, Loki, Tempo and Prometheus, persistent in a separate `telemetry_data` volume. It can require around a gigabyte of local disk space for the container image and additional disk for stored data.
- Grafana is bound only to Mac loopback port `13000`. The default Grafana local login is `admin/admin` unless changed; do **not** expose the dashboard publicly.
- Only OTLP HTTP port 4318 is accessed from the internal Docker network. Do not forward it to the public internet.
- No request or business message content, tokens, proof IDs, lead IDs or employee IDs should be shipped to telemetry. Database audit records (with IDs and proof) remain behind the authenticated application API.
- A 5xx error sets the trace status without emitting exception bodies, which might contain personal content.

## Reproducible Mac exercise, without changing the regular Compose file

The Mac owner's local `compose.yaml` currently has an uncommitted host port override `127.0.0.1:18080:8000`. **Keep it unchanged**.

The optional LGTM overlay does not replace or edit that file:

```bash
git pull --ff-only
docker compose -f compose.yaml -f compose.telemetry.yaml config --quiet
docker compose -f compose.yaml -f compose.telemetry.yaml up --build -d
docker compose -f compose.yaml -f compose.telemetry.yaml ps
```

Then get a correlation ID (the token is local, synthetic demo only):

```bash
curl -i -H "Authorization: Bearer dev-only-supervisor-token" \
  http://127.0.0.1:18080/api/v1/overview
```

Record the `X-Trace-Id` response header. Optionally generate additional workflow traffic from the UI (do **not** re-seed if the original sample is already imported).

Open [Grafana localhost:13000](http://127.0.0.1:13000), sign in locally, and use **Explore**:
1. **Tempo** trace lookup with the exact response `X-Trace-Id`: expect a sanitized HTTP route, response status, no raw request data.
2. **Loki** logs for service `supportpulse-ai` and match the trace ID: inspect safe `http.completed` JSON.
3. **Prometheus** search for `supportpulse_http_requests` and `supportpulse_http_duration_ms` metric families after collector interval (5s). Ensure no user/source/lead ID labels.

**Critical QA step:** visually confirm all three signals are **present in the Grafana UI** and share the same trace ID for one request before labeling Observability 2/2. Test actual delivery rather than treating Docker startup or unit mocks as proof. Share screen captures of Grafana Explore for source-linked peer-review evidence; redact any credentials if accidentally visible.

Stop only the overlay's collector without touching PostgreSQL if you need to conserve disk/memory:
```bash
docker compose -f compose.yaml -f compose.telemetry.yaml stop telemetry
```
Do not use `docker compose down -v` because it would erase named volumes holding test data.

## Technical references

- https://grafana.com/docs/opentelemetry/docker-lgtm/
- https://opentelemetry.io/docs/languages/python/
- https://github.com/DataTalksClub/ai-dev-tools-zoomcamp/blob/main/project/README.md

## Limits

1. No real Grafana view asserted until owner test; local CI asserts formatting, correlation and build/tests, not ingestion through LGTM.
2. No user-impact alert, on-call agent, CI/CD deployment or live customer source yet.
3. Current operations remain SYNTHETIC_ONLY and production_ready=false.
