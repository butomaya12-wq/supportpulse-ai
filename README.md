# SupportPulse AI — explainable customer-follow-up control

**Status: Engineering iteration 001 / synthetic local demo / NOT production-ready.**

SupportPulse AI is an independent application under development at Maya AI Systems. It aims to help teams identify a verifiable broken commitment in a customer conversation, confirm a case with a human reviewer, assign remediation, and track a source-confirmed action. The larger product vision includes AI-assisted communication quality and operational economics; those features are NOT implemented here.

This codebase is original and separate from the existing HandoffGuard AI project. No live messenger, CRM integration, autonomous staff scoring, actual recovered revenue, hosted deployment or real customer data is included.

## What is implemented in this first slice

- Backend: Python FastAPI, SQLAlchemy persistence, role-scoped synthetic demo API.
- Frontend: responsive English/Russian dashboard with real API-driven counters, source health, case queue and evidence detail.
- Database: PostgreSQL via Docker Compose, SQLite supported for local tests.
- Ingestion: bounded synthetic events, unique provider keys and conflict rejection.
- Business logic: **human-approved** explicit due date, 30-minute source-watermark guard, candidate overdue vs unknown, review, task assignment and verified provider send event.
- Integrity: tenant-scoped reads, role restrictions, append-only audit events, missing-data abstention and null financial impact.

## Quick start — Docker and Postgres

Requirements: Docker Engine and Docker Compose plugin.

```bash
# No external customer data. Default demo tokens are insecure and LOCAL ONLY.
docker compose up --build -d
# Open http://127.0.0.1:8000
```

For the local test screen, use `dev-only-supervisor-token` in the token field unless overridden with `SP_SUPERVISOR_TOKEN` in a local `.env` file. These are intentionally **demo-only** example values, never production credentials. Docker Compose binds the app to `127.0.0.1` only.

Click **Load example** to import the initial event and identify a candidate overdue quote. Open the case, **confirm** the missed commitment and **assign** it. Click **Import correction**, then **Verify** the provider event with `msg-003`. Only sending is verified, NOT receipt, payment or recovered revenue.

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
