# SupportPulse AI — explainable customer-follow-up control

**Status: Engineering iteration 004 / synthetic local demo / NOT production-ready.**

SupportPulse AI is an independent application under development at Maya AI Systems. It aims to help teams identify a verifiable broken commitment in a customer conversation, confirm a case with a human reviewer, assign remediation, and track a source-confirmed action. The larger vision includes omnichannel communication quality and operational economics; those broader capabilities are NOT implemented. Iteration 004 introduces source-linked promise **proposals**, still requiring human approval.

This codebase is original and separate from the existing HandoffGuard AI project. No live messenger, CRM integration, autonomous staff scoring, actual recovered revenue, hosted deployment or real customer data is included.

## What is implemented in this first slice

- Backend: Python FastAPI, SQLAlchemy persistence, role-scoped synthetic demo API.
- Frontend: responsive English/Russian dashboard with real API-driven counters, source health, case queue and evidence detail.
- Database: PostgreSQL via Docker Compose, SQLite supported for local tests.
- Ingestion: bounded synthetic events, unique provider keys and conflict rejection.
- Business logic: **human-approved** explicit due date, 30-minute source-watermark guard, candidate overdue vs unknown, review, task assignment and verified provider send event.
- Integrity: tenant-scoped reads, role restrictions, append-only audit events, missing-data abstention and null financial impact.
- Iteration 004: read-only promise proposals from immutable manager messages, strict source/time validation, explicit human approval; deterministic baseline by default (**not a real LLM**), optional off-by-default real-model adapter not evaluated with live model calls.

## Quick start — Docker and Postgres

Requirements: Docker Engine and Docker Compose plugin.

```bash
# No external customer data. Default demo tokens are insecure and LOCAL ONLY.
docker compose up --build -d
# Open http://127.0.0.1:8000
```

For the local test screen, use `dev-only-supervisor-token` in the token field unless overridden with `SP_SUPERVISOR_TOKEN` in a local `.env` file. These are intentionally **demo-only** example values, never production credentials. Docker Compose binds the app to `127.0.0.1` only.

Click **Load example** to import the initial event and identify a candidate overdue quote. Open the case, **confirm** the missed commitment and **assign** it. Click **Import correction**. The case then offers **Verify** with the matching `msg-003` proof; the verify button stays unavailable before source proof exists. Only sending is verified, NOT receipt, payment or recovered revenue.

```bash
# Optional terminal API checks (synthetic only)
curl http://127.0.0.1:8000/health
curl -H 'Authorization: Bearer dev-only-supervisor-token' http://127.0.0.1:8000/api/v1/overview
```

Do not expose this app to the internet; it uses a local demo auth scheme and lacks production privacy, rate-limits, migrations and operational safeguards.

## Alternative: local Python and SQLite

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
make test
make dev
```

The SQLite file stays in the working folder and is ignored by Git. Environment-variable `DATABASE_URL` can select an alternative database; Docker Compose uses PostgreSQL.

## Reviewer quick checks

1. `/health` says `production_ready=false` explicitly.
2. `POST /api/v1/demo/seed` (local supervisor auth) creates a candidate, not a confirmed staff failure.
3. A supervisor explicitly reviews a case, then creates an action.
4. `POST /api/v1/demo/followup` imports an actual **synthetic provider event**; action verification requires its external ID.
5. Repeat the same import — no duplicate source events or commitments.
6. Degrade source coverage or move watermark before grace — result is `INSUFFICIENT_DATA`, not `CONFIRMED_OVERDUE`.
7. Dashboard shows an unavailable on-time percentage and `impact_rub=null` when evidence is insufficient.

## Documentation

- [Design spec and acceptance criteria](docs/SCENARIO_SPEC_v0.2.md)
- [Product discovery](docs/PRODUCT_DISCOVERY_v0.1.md)
- [Architecture, trust boundaries, known gaps](docs/ARCHITECTURE.md)
- [AI-assisted engineering team and owner gates](docs/AGENT_TEAM.md)
- [Development backlog](docs/BACKLOG.md)
- [Course rubric and gap map](docs/COURSE_MATRIX.md)
- [Evidence/acceptance traceability](docs/TRACEABILITY.md)
- [Buyer discovery questions](docs/BUYER_DISCOVERY.md)
- [Agent process and guardrails](AGENTS.md)
- [Guarded AI promise proposals and evaluation limits](docs/AI_PROMISE_EXTRACTION_v0.1.md)

## Publishing a *new* GitHub repository

The connected GitHub integration in this environment does not offer repository creation. Do **not** push these files to an existing project. Create `supportpulse-ai` separately, keep the GitHub repository empty (do not initialize a README), extract this ZIP, and from the project directory run:

```bash
git init -b main
git add .
git commit -m "feat: initialize independent synthetic SupportPulse vertical slice"
git remote add origin https://github.com/butomaya12-wq/supportpulse-ai.git
git push -u origin main
```

**That URL does not exist until the repository is created by its owner.** After creation, issue planning can be uploaded with `scripts/create_issues.sh` using GitHub CLI after authentication. The `.github/workflows/ci.yml` workflow starts running only after push.

## Validation snapshot (22 October 2026)

`pytest -q`: 14 tests passed locally using SQLite in-memory and FastAPI TestClient; actual HTTP `/health` returned 200; JavaScript syntax passed. Docker/real PostgreSQL startup and browser end-to-end tests are **not** verified in this environment. See `docs/TRACEABILITY.md`.

## Product research status

Discovery documents are hypotheses. There are no verified buyer interviews or permissions for real sources in this codebase. Data minimization and operational / employee fairness review are mandatory before commercial use.

## Iteration 002 verification UX and PostgreSQL checks

The case-detail API returns `verification` with `ready`, `proof_external_id`, and a `reason` code. The dashboard only enables verification when qualifying source evidence is present and continues to require explicit human confirmation. User-facing errors and denominator descriptions explain the synthetic limitation. CI adds an isolated PostgreSQL service with idempotence and degraded-coverage checks. These are engineering tests, not production readiness.

## Iteration 004 — evidence-first AI promise proposals

The new dashboard panel **«Предложения по обещаниям»** accepts synthetic source and conversation IDs. Try `demo-instagram` and `demo-lead-001` after loading the example. It displays a source-linked quote and explicit due time; only the supervisor can select **«Проверить и утвердить человеком»**. The original deterministic approval and evaluation pipeline remains unchanged.

**Important:** the default `SP_AI_PROVIDER=rules` is an explicitly labeled **deterministic baseline, not an LLM**. A genuine OpenAI Responses API JSON-Schema adapter exists, but is **not selected in Docker/CI, has not been invoked with a live model, and must not be described as a verified AI capability**. Model output is always validated against immutable source text and due time; on ambiguity, abstain. The workflow remains synthetic-only, and no third-party messages are sent by default.

For exact API sample, safety properties, environment opt-in, and tiny synthetic evaluation see [AI promise extraction spec](docs/AI_PROMISE_EXTRACTION_v0.1.md). The test evidence is not proof of model accuracy, financial recovery, or production readiness.

## Iteration 005 — privacy-preserving OpenTelemetry (opt-in)

The regular demo remains synthetic-only. OpenTelemetry is disabled in normal Docker Compose, but structured scrubbed JSON operation logs and a trace correlation header are available. An **optional** `compose.telemetry.yaml` overlay adds Grafana/Loki/Tempo/Prometheus behind Mac localhost and emits correlated traces, metrics and log events. It **does not modify your existing compose.yaml host-port override or Postgres volume**.

Review the [observability walkthrough and privacy checklist](docs/OBSERVABILITY_v0.1.md) before using the optional overlay. **Do not count course Observability 2/2 until the 3 signals are verified in the actual Grafana UI.** No production-grade hosted monitoring or impact alert exists yet.

## Iteration 006 — synthetic user-impact alert exercise

An optional Grafana-managed alert monitors HTTP **5xx** on the supervisor's critical `GET /api/v1/overview` endpoint. A doubly opt-in, supervisor-authenticated synthetic request can generate 503 **for that request only** to prove the alert fires; other viewers and your persistent Postgres data stay unchanged. Ordinary Compose and telemetry Compose do not enable the drill.

Review [safe Grafana alert trigger and recovery runbook](docs/ALERT_DRILL_RUNBOOK.md). File provisioned rule lives in [ops/grafana/alerting/overview-5xx.yaml](ops/grafana/alerting/overview-5xx.yaml) and optional third overlay is `compose.alerts.yaml`. This is a **simulated local incident**, not proof of a real customer outage, external notification or on-call agent. **Do not award the course alerting point until an owner screenshot confirms Normal → Firing → Normal.**

## Iteration 007 — bounded local Grafana on-call responder

A separate, synthetic-only `oncall` service can consume **real Grafana webhook notifications** when enabled through `compose.oncall.yaml`. Grafana sends them only for the existing critical overview 5xx alert through a dedicated contact point, with a locally generated private webhook secret. The responder performs fixed **read-only health and overview checks**, deduplicates replays, saves a sanitized operational audit and verifies recovery only when Grafana reports resolved and both probes pass.

**Status:** implemented in code, **real Grafana-to-webhook delivery on Mac still requires user acceptance**. This is deterministic runbook automation, **not an autonomous code-repair agent** and not a live LLM. Do not confuse safe diagnosis with successful remediation.

Follow [the on-call setup and acceptance guide](docs/ONCALL_AGENT_v0.1.md) before running the additional overlay; the instructions avoid replacing the owner's Mac-specific compose.yaml or erasing the existing Postgres volume.

## Iteration 007B — synthetic on-call **repair** demonstration

The agent can now correct one explicitly armed **synthetic-only** dashboard outage, rather than merely diagnosing alerts. On real Grafana `firing`, it verifies normal overview HTTP 503, confirms the separate repair-drill gate is `BROKEN`, invokes a single secret-authenticated revision-checked `repair` endpoint, and verifies the same overview returns HTTP 200. The oncall SQLite audit records `AUTO_REPAIRED_SYNTHETIC`, the before/after HTTP status and gate revision; a later `resolved` webhook must independently confirm recovery.

**This does not fix arbitrary production faults**, contains no LLM code-writing/restart/redeployment privilege, and is disabled unless `compose.repair.yaml` is explicitly added with a **separate** high-entropy local repair token. All business PostgreSQL records and older synthetic cases are untouched.

See [real synthetic alert-to-repair evidence guide](docs/ONCALL_REPAIR_DRILL_v0.2.md). **On-call course points remain unclaimed until a full real local Grafana alert → agent fix → verified resolution is observed and documented.**
