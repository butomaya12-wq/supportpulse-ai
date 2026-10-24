# Iteration 009A — isolated staging API security gate

**Status: IMPLEMENTATION PR — NOT DEPLOYED, NOT PRODUCTION APPROVED.**
Owner: Maya AI Systems. This document scopes the first code slice of [Issue #21](https://github.com/butomaya12-wq/supportpulse-ai/issues/21).

## Why a second ASGI application

The existing `app.main:app` is an intentionally writable **localhost** synthetic testbed:
it defaults to demo Bearer tokens, runs `create_all` at startup and includes
mutation/repair/on-call endpoints. It must never be reused as a public Render service.

`app.cloud:app` is a **different** ASGI entrypoint with exactly:
- Public liveness: `GET /health` (no database details, no customer records).
- Secret-gated readiness: `GET /api/v1/reviewer/ready` (read-only PostgreSQL checks).
- Secret-gated tenant-scoped metrics: `GET /api/v1/reviewer/overview`.
- Secret-gated tenant-scoped evidence: `GET /api/v1/reviewer/findings`, limit 1–50.

**No write endpoints, fixture seeding endpoint, legacy token login, API docs,
repair drill, Grafana webhook, on-call handler or browser-exposed authentication token.**
The public static reviewer preview from iteration 008 remains independent and unchanged.

## Required runtime conditions (all fail closed)

| Variable | Meaning |
|---|---|
| `SP_MODE=synthetic_staging` | Cannot be `synthetic_local` or `production` |
| `SP_STAGING_SYNTHETIC_ONLY=YES` | Explicit gate: no customer content |
| `DATABASE_URL` | Dedicated isolated `postgresql+psycopg://...` URL; use the **read-only database role** |
| `SP_STAGE_REVIEWER_TOKEN` | Dedicated randomly generated ASCII secret, >= 48 characters, Render secret setting; never commit it |
| `SP_STAGE_ALLOWED_HOSTS` | Comma-separated exact trusted hostnames; no wildcard |
| `RENDER_GIT_COMMIT` | Exact immutable 40-character deployed commit SHA for auditability |

Generate the new reviewer token **on a trusted administrator machine**, not in a
web form or GitHub code, with `python3 -c 'import secrets; print(secrets.token_urlsafe(48))'`.
Store it only in the provider's secret manager; do not copy its value into chat,
commits, CLI screenshots or public CI logs. Never reuse `SP_SUPERVISOR_TOKEN`,
`SP_MANAGER_TOKEN`, `SP_ONCALL_WEBHOOK_TOKEN`, or `SP_REPAIR_TOKEN`.

### Runtime image

`docker build -f Dockerfile.staging -t supportpulse-stage .`

The staging image starts `app.cloud:app` on port 10000 as non-root user 10001,
without copying the local fixtures. It cannot start without the required staging
configuration. No cloud service or cloud database is provisioned by this PR.

## Authentication and HTTP boundary

- Reviewer access uses a long random server-side secret. All data endpoints return
  401 without it. The identity is a fixed **synthetic read-only reviewer** role,
  not a real customer or production account.
- The app enforces an exact Host allowlist; disables CORS and interactive API docs;
  emits no-store, no-sniff, frame-denial, no-referrer, CSP and HSTS headers.
- A **per-process** 60-request/minute limit applies after successful authorization.
  It is a basic abuse-control layer, **not** multi-instance or IP-aware DDoS protection.
- No session cookie is issued; therefore no browser CSRF token applies to these
  header-authenticated GET-only operations.
- Use Render HTTPS for all external access. Require TLS/private networking to
  PostgreSQL and platform-level edge rate limiting/abuse protection before exposure.
- The legacy application still has its localhost-only deliberately unsafe demo
  token defaults. Never point a cloud service at the legacy Dockerfile.

## Database and release prerequisites: NOT YET DONE

1. Provision a **separate synthetic-only staging database**. Choose geography,
   retention, backup plan, and expected monthly charges first.
2. Add reviewed forward schema migrations and a dedicated migration role;
   remove dependence on live startup `create_all`. This staging reader itself
   deliberately performs **no migrations** and cannot seed data.
3. Create a distinct least-privilege DB login with `CONNECT`, schema `USAGE` and
   `SELECT` only (no INSERT/UPDATE/DELETE/CREATE). Confirm table grants and
   connection restrictions; test with real PostgreSQL. Populate only vetted,
   synthetic fixtures through a separately authorized one-off administration job.
4. Implement individually attributable reviewer identities (e.g. managed OIDC),
   stronger distributed rate limits/audit, rotation and revocation before exposing
   sensitive datasets. Shared Bearer credential is staging-only.
5. Configure cloud staging service with CI-gated deployment after required GitHub
   checks pass. Current public static preview still deploys on `commit`.
6. Configure **protected GitHub production environment with required human reviewer**
   and branch restrictions **before** adding a production deployment action.
   An unprotected `environment: production` YAML line alone is NOT approval.
7. Add immutable artifact/image digest, real external HTTPS staging smoke checks,
   browser evidence against *real staging API*, release history and rollback drill;
   document DB forward-only migration and point-in-time recovery constraints.
8. Perform explicit security review before enabling production; default remains
   **DISABLED**. Do not onboard real customer content without consent/DPA.

## CI evidence in this slice

- Unit: startup refuses unsafe modes, local tokens, SQLite, wildcard Host and
  missing release SHA; auth, header, no-write route assertions and request throttle.
- PostgreSQL integration: read-only staging API GETs against dedicated throwaway
  CI PostgreSQL; no write via HTTP; unrelated tenant not returned.
- Docker: separate `Dockerfile.staging` builds alongside original local images.
- The existing browser E2E, local Compose, Grafana/on-call and static preview
  checks remain in place.

**Acceptance for 009A:** tests green in PR; developer review complete; main and
public static preview unchanged. **Issue #21 remains OPEN** until cloud
deployment, DB isolation/migration, actual release gates and rollback are proved.

## Rollback for this code-only slice

Do not merge if tests regress. To abandon: close the PR, leave `main` unchanged.
After eventual merge, revert the isolated staging entrypoint PR if necessary.
This is a **code rollback**, not evidence of a successful deployed application
rollback or reversible DB migration.
