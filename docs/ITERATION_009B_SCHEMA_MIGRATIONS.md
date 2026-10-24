# Iteration 009B — staging PostgreSQL schema migrations

**Status: CODE/CI MIGRATION PREPARATION. No customer database or Render database touched.**
Part of [Issue #21](https://github.com/butomaya12-wq/supportpulse-ai/issues/21).

## What changed

- Dedicated `Alembic` migration path and immutable initial revision
  `sp_0001_baseline` for all six application tables:
  `sources`, `source_events`, `commitments`, `findings`,
  `corrective_actions`, `audit`.
- `app.cloud:app` from 009A stays read-only and runs **no startup
  `create_all`**. Migration administration is a separate operation.
- `migrations/env.py` refuses unexpected modes, non-PostgreSQL targets,
  database names not explicitly identifying staging, wrong expected database
  name and missing explicit migration acknowledgments.
- CI uses a disposable PostgreSQL instance, runs upgrade → schema drift
  check → version/table assertion → production-mode refusal → downgrade
  (CI only) → re-upgrade. This does **not** prove production database rollback.

## How a future administrator will apply this to a NEW EMPTY STAGING database

**Do not run these commands against the existing local Mac database,
customer data, a production DB, or any database with existing schema.**
Required before executing:

1. Approve staging DB provider, cost, region, retention, backup policy, TLS,
   access controls, and synthetic-only data policy.
2. Provision a new **empty** PostgreSQL database with a name that contains
   `stage` or `staging` and distinct migrator and application users.
3. Take a baseline snapshot/backup and confirm no business records exist.
4. Put all secrets in environment configuration/secret manager rather than
   shell history or GitHub. The following environment variables must already
   be set securely by the operator:

```text
SP_MODE=synthetic_staging
SP_STAGING_SYNTHETIC_ONLY=YES
SP_SCHEMA_MIGRATE_CONFIRM=MIGRATE_ISOLATED_STAGING_ONLY
SP_SCHEMA_MIGRATION_ROLE=migrator
SP_STAGE_DB_NAME=<exact-new-stage-database-name>
DATABASE_URL=<secret PostgreSQL psycopg URL for dedicated migration role>
```

```bash
python -m pip install -r requirements-migrate.txt
alembic upgrade head
alembic check
alembic current
```

Then create **a separate read-only database role** with only `CONNECT`,
schema `USAGE` and `SELECT` on authorized tables; grant no schema creation,
writes or destructive privileges. Configure `app.cloud:app` with that
read-only connection, and verify schema availability via its authenticated
`GET /api/v1/reviewer/ready` endpoint.

## Safety and rollback

- Never run `alembic stamp head` on an arbitrary existing database: it can
  falsely label incompatible schema as migrated.
- `downgrade()` for initial revision drops all application tables. It exists
  **only** for truly disposable CI; do not use it to roll back a staging or
  production deployment holding data.
- Real release rollback means restore a known-good prior app image SHA with
  a backward-compatible **forward** schema, and use point-in-time DB recovery
  only under an approved incident runbook. Both are **still TODO**.
- Automated CI checks schema vs current SQLAlchemy models; schema drift
  should fail rather than silently creating missing tables at runtime.
- This versioned migration has not been executed on a persistent cloud
  database. No live API URL or per-user reviewer identity exists yet.

## Evidence for 009B

Dedicated GitHub `schema-migration` CI job against ephemeral PostgreSQL
will record the exact successful migration run. Existing 009A tests must
continue passing. Issue #21 remains open until independent cloud deployment,
CI-gated staging, approved production release and rollback are proven.
