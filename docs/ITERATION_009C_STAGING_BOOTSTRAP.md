# Iteration 009C — reproducible synthetic staging, before Render activation

**State: code merged; isolated Free cloud PostgreSQL provisioned but schema and runtime API NOT deployed. No customer data.**
Parent: [Issue #21](https://github.com/butomaya12-wq/supportpulse-ai/issues/21).

## What ships

- `scripts/bootstrap_staging.py` runs **only** against an acknowledged **new, empty** PostgreSQL database whose name contains `stage` and matches `SP_STAGE_DB_NAME`.
- The database must already have explicit Alembic revision `sp_0001_baseline`; do not run `create_all` or auto-migrate from the public web worker.
- It inserts **one** existing synthetic fixture from `fixtures/initial.json`, evaluates a single `CANDIDATE_OVERDUE` case, and makes a new `supportpulse_stage_reader` login restricted to `SELECT` on the six synthetic tables. No fake ROI or external customer data.
- The new role has no write, schema-create, database-create or role-management privileges. CI checks actual rejected write and DDL operations using its login.
- `scripts/smoke_staging.py` probes live HTTP: unauthenticated 401, authenticated ready/overview/findings, exactly one synthetic candidate, no demo mutation/repair endpoints, optional immutable SHA.
- `render.staging.yaml` is a **draft**, not applied. Separate **Free Render web service** with `autoDeployTrigger: checksPass`, Dockerfile.staging, explicit allowed hostname and placeholder for independent database reader URL and reviewer credential. Existing public static site isn't included or modified.

## Provider limits and decision

Render Free web and Postgres are for **temporary disposable testing only**. Free Postgres expires after 30 days, stores at most 1 GB and has **no managed backups**. It is not suitable for real data. Do not upgrade, introduce paid plans or attach persistent customer content without separate human cost and security approval. Read current provider policy before any future provisioning.

## Two-phase provisioning: do NOT apply the Blueprint first

1. In the confirmed Render workspace create a **separate** PostgreSQL 16 Free instance in `virginia` with actual database name `supportpulse_stage_cloud` (avoid accidentally using the Render *service* display name as DB name). Check expected expiry date and actual billing plan in the Dashboard. Never reuse local Mac databases or another app's Postgres.
2. On a trusted workstation with Render's **owner/migration connection string** in local protected environment (never paste it into chat), convert the URL scheme `postgresql://` to `postgresql+psycopg://` for this repository's SQLAlchemy driver. Use approved SSL/private routing and never echo the password.
3. For the dedicated admin command session supply exactly:

```text
SP_MODE=synthetic_staging
SP_STAGING_SYNTHETIC_ONLY=YES
SP_STAGE_DB_NAME=supportpulse_stage_cloud
SP_SCHEMA_MIGRATE_CONFIRM=MIGRATE_ISOLATED_STAGING_ONLY
SP_SCHEMA_MIGRATION_ROLE=migrator
SP_STAGE_BOOTSTRAP_CONFIRM=BOOTSTRAP_NEW_DISPOSABLE_STAGE_ONLY
SP_STAGE_READ_PASSWORD=<unique randomly generated 48+ ASCII chars; never commit>
DATABASE_URL=<secret owner/migrator PostgreSQL+psycopg URL>
```

4. Check DB is genuinely empty and stage-scoped, then run (no default production fallback):

```bash
python -m pip install -r requirements-migrate.txt
alembic upgrade head
alembic check
python -m scripts.bootstrap_staging
```

5. **Before connecting a public web service** independently verify that `supportpulse_stage_reader` can SELECT but cannot UPDATE, INSERT, CREATE TABLE or read other tenant data via the API. It must use its own secret password and its own `postgresql+psycopg://` URL. Never send the migration-owner URL to web runtime.
6. Open Render Dashboard and create/apply the **staging-only** `render.staging.yaml` Blueprint from the repository. The generated web service must be plan `free`, named `supportpulse-ai-stage-reader`; manually supply the two `sync: false` secrets: `DATABASE_URL` (READ-ONLY role) and `SP_STAGE_REVIEWER_TOKEN` (new unique randomly generated 48+ ASCII characters). If the allocated host differs from the configured hostname, update `SP_STAGE_ALLOWED_HOSTS` before testing.
7. Confirm Render really reports `autoDeployTrigger=checksPass` and successful CI for the exact release SHA. Public HTTPS smoke must use an explicitly protected operator secret in GitHub Actions/secure workstation; never embed it into the existing static preview or a public browser.
8. Run `STAGING_API_URL=https://<actual-render-stage-host> python scripts/smoke_staging.py` from a trusted operator environment with `SP_STAGE_REVIEWER_TOKEN` and `EXPECTED_STAGE_SHA` available as secrets. Save Git SHA, Render deploy ID, HTTPS status, missing unauthorized access and timestamp.
9. Verify independent rollback to the last successful **application image** commit only after capture of a deploy/history checkpoint and with schema compatibility. Do not perform destructive `alembic downgrade` on the hosted DB. Production remains explicitly DISABLED until separate human approval gate is tested.

## Access limitations

The temporary reviewer token is shared and does not identify each person. It is NOT appropriate for multi-tenant real customers. Before real data, add individual authentication, audit, distributed rate limiting, protections against brute force, data retention rules and legal basis for processing customer content. The current fixed `demo-studio` tenant is synthetic by contract only.

**Do not mark #21 complete just because code CI passes.** The hosted DB and hosted read-only API, actual CI-gated deploy, browser proof and real rollback still need verified evidence.

## Measuring project time

The canonical ledger is `docs/DEVELOPMENT_TIMELOG.md`. Its first planning artifact and provisional engineering-start timestamps remain unchanged. Log this iteration's GitHub PR and CI milestones as **observed engineering events**, not user hands-on hours. Resume human time tracking with explicit non-overlapping working sessions and breaks.

## Verified 25 October 2026 milestone (UTC)

- [PR #24](https://github.com/butomaya12-wq/supportpulse-ai/pull/24) was merged as `1e5132a0b27e8dbf154007ec62756fb2c637c68e` at **17:14:57 UTC**. PR CI **5/5 passed** (API, Compose/Docker, PostgreSQL, migration + live HTTP staging smoke, browser E2E).
- Render created a separate database resource: **`supportpulse-stage-cloud`**, id `dpg-dbf3ia8ae00c73el56r0-a`, PostgreSQL **16**, region **virginia**, plan **free**, actual db name `supportpulse_stage_cloud`. [Render database dashboard](https://dashboard.render.com/d/dpg-dbf3ia8ae00c73el56r0-a).
- **Free DB created at 2026-10-25 17:15:21 UTC; expires 2026-11-24 17:15:21 UTC.** It has no managed backups. At the last inspection it was still `creating`.
- The provider returned `ipAllowList: []`: external queries were blocked. A read-only connectivity attempt failed because no external address is allowlisted. **No migration, SQL bootstrap, role or synthetic fixture has been applied to the Render database.** The previous CI proof used **disposable GitHub Actions PostgreSQL**, NOT this newly created cloud DB.
- **Next owner-assisted step:** after Render reports available, allowlist the trusted Mac's current public IP temporarily in Render Networking; securely copy the database **external URL** into a shell environment on that Mac (never to chat). Run the reviewed explicit migration/bootstrap commands above, then restore the most restrictive network rules compatible with the deployed API's private connection. Do not allow `0.0.0.0/0`.
- No Render web service or Blueprint has been activated. No paid resources created. The existing [public static reviewer demo](https://supportpulse-ai-review-demo.onrender.com) remains independent.

**Important distinction:** cloud database resource existence is not evidence of schema readiness or an operational remote API.
