# SP-019: Critical overview 5xx — synthetic-only Grafana alert drill

This is a **controlled simulation** of a user-visible failure. It is not evidence of a real customer outage, nor does it page a real responder. It demonstrates a reproducible Grafana rule evaluating actual HTTP 5xx telemetry from the **same** protected route normally used by the dashboard.

## Impact hypothesis and evidence

A business supervisor cannot read **`GET /api/v1/overview`** if that request returns `503`. No overview → cannot see overdue customer commitments → corrective workflow may be delayed. This is the *plausible business consequence*, not a measured financial loss or client incident.

Grafana queries the collected OpenTelemetry Prometheus metric **`supportpulse_http_requests_total`** with static labels `http_route=/api/v1/overview`, `http_request_method=GET`, `http_response_status_class=5xx`. Its rule checks for any increased 5xx over two minutes, evaluates every ten seconds and shows **Firing** (no pending window). After errors cease, it returns to **Normal** when the two-minute window expires. `NoData` is OK: a quiet synthetic demo isn't a proven outage.

The **Loki** HTTP completion log and **Tempo** span carry the same request trace ID as the response header. No messages, token or customer IDs are exported as telemetry attributes or labels.

## Safety fence

- Requires `SP_MODE=synthetic_local` **and** `SP_FAULT_DRILL_ENABLED=1` **and** successful supervisor authentication **and** exact HTTP header `X-SupportPulse-Drill: overview-503`. All four are required.
- The drill returns 503 only to **that explicitly marked HTTP request**. It does not change global app state, alter database content, stop PostgreSQL, change existing synthetic cases, or affect normal dashboard requests.
- No app restart, incident recovery or deployment is caused by the alert. The user must not confuse intentional 503 with a live outage.
- Only the additional `compose.alerts.yaml` overlay enables the drill and adds a Grafana-managed alert rule; standard `compose.yaml` or `compose.telemetry.yaml` alone leaves it disabled.
- The overlay does not contain API keys. Alerting uses Grafana UI state; **no external email/webhook notification is configured**, so there is no guarantee that a person is notified. The on-call responder is a future separate iteration.

## Setup (Mac, owner-controlled, existing database remains unchanged)

Keep the owner's uncommitted `compose.yaml` mapping `127.0.0.1:18080:8000`. DO NOT run `docker compose down -v`:

```bash
git pull --ff-only
docker compose -f compose.yaml -f compose.telemetry.yaml -f compose.alerts.yaml config --quiet
docker compose -f compose.yaml -f compose.telemetry.yaml -f compose.alerts.yaml up --build -d
docker compose -f compose.yaml -f compose.telemetry.yaml -f compose.alerts.yaml ps
```

Open `http://127.0.0.1:13000` → **Alerting → Alert rules**; locate **SupportPulse: critical overview returns HTTP 5xx** in folder **SupportPulse AI**. The rule is provisioned read-only from `ops/grafana/alerting/overview-5xx.yaml`; it should initially be **Normal**. If missing, check telemetry container status/logs; Grafana file provisioning occurs on startup. If datasource errors occur, verify Grafana default Prometheus datasource UID is `prometheus`. Do not mark any rule as verified until it is visibly loaded with a successful evaluation.

### Trigger *only* a synthetic user-facing 503

Make sure the response for an ordinary supervisor request is still 200:

```bash
curl -sS -o /dev/null -w 'ordinary_overview_http=%{http_code}\n' \
  -H 'Authorization: Bearer dev-only-supervisor-token' \
  http://127.0.0.1:18080/api/v1/overview
```

Generate several opt-in errors for the alerting evaluation:

```bash
for i in 1 2 3 4 5 6 7 8 9 10 11 12; do
  curl -sS -o /dev/null -w 'drill_http=%{http_code}\n' \
    -H 'Authorization: Bearer dev-only-supervisor-token' \
    -H 'X-SupportPulse-Drill: overview-503' \
    http://127.0.0.1:18080/api/v1/overview
  sleep 2
done
```

Only expected drill `503` responses count as deliberate simulated failures. Grafana → **Alert rules** → the rule: observe **Firing**. In Grafana Explore → Prometheus execute:

```promql
sum(increase(supportpulse_http_requests_total{http_route="/api/v1/overview",http_request_method="GET",http_response_status_class="5xx"}[2m])) or vector(0)
```

There should be a positive value after traffic and metric collection. The dashboard remains working without the special header. **Don't supply raw secrets or message text in screenshots.**

### Recovery evidence

Stop the drill loop. Re-run an ordinary request without `X-SupportPulse-Drill`: **200**. When Grafana no longer sees 5xx in the two-minute window, the rule should recover to **Normal**. Capture (1) initial Normal, (2) Firing from positive 5xx Prometheus metric, (3) recovered Normal, and for one failing request (4) `X-Trace-Id` with a redacted Loki `http.completed` and Tempo 503 span. These are runtime evidence, not CI or screenshots of configuration alone.

## Runbook / reaction

1. **Identify scope**: check if this is explicitly tagged `stage=synthetic-only`; never page or punish a real person for the controlled drill.
2. **Verify alert cause**: Grafana rule and actual `5xx` Prometheus count on route `GET /api/v1/overview`; correlate to a Tempo span and Loki `http.completed` by `trace_id`. **4xx deliberate evidence gates do not mean this incident.**
3. **Check user impact**: normal (non-drill) overview should return 200. If it does, classify as `DRILL_ONLY`, not a live incident. If it does not, stop and investigate independently; do not attempt automated changes.
4. **Safe diagnostic action**: fetch `/health` and `/api/v1/sources/health` only if available; never modify source events, manager reviews or customer contacts.
5. **Recovery**: stop sending the special header; inspect rule return to Normal; record trace, metric, timing and conclusion. No automatic restart, DB repair, deploy or customer notification without separate human approval.

## Verification status

- CI validates safe 503 double opt-in, role checks, non-mutation, 5xx metrics and correct Grafana YAML structure.
- **Grafana alert actually provisioned and fired on owner's Mac?** Not proven until owner screenshots and actual Prometheus query results.
- **Notification or alert-driven on-call agent?** Not implemented.
