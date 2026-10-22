# SupportPulse AI — Architecture v0.1

## Local synthetic vertical slice

`browser (vanilla JS, HTML, CSS)` -> `FastAPI` -> `SQLAlchemy` -> `PostgreSQL (Docker Compose)`.

The same code can be tested locally with SQLite. **PostgreSQL is the intended Docker runtime**, not evidence that PostgreSQL integration tests have been run in this environment. The UI deliberately requires a local demo Bearer token; these are NOT production credentials or production authorization.

## Core operations

1. Import a bounded batch of synthetic normalized source events; ensure `(tenant, source, external_id)` uniqueness; never overwrite conflicting evidence.
2. Supervisor explicitly approves commitment from a manager-message source ID with an absolute timezone-bearing due date. NLP/LLM extraction is NOT implemented.
3. Evaluator compares source watermark and health with the approved due date and 30-minute allowance, then checks for quote-sent events from the same actor and conversation.
4. Candidate overdue -> human review -> corrective assignment -> authenticated synthetic provider event -> verified sending. **Verified sending is not verified delivery or recovered revenue**.
5. Aggregate operational KPIs with declared denominators; financial effects remain null.

## Trust boundaries

Demo-only tokens resolve to a server-side fixed tenant/role. All database reads filter by tenant, with manager view restricted to own cases. This is a **limited synthetic access scheme**, not enterprise auth or production multi-tenancy. No real contacts, secrets, logs or provider connector may enter this demo. The API binds only to `127.0.0.1` in Compose; production mode is rejected at startup.

## Known gaps / non-claims

- No migration framework yet (startup `create_all` is dev-only).
- No identity resolution across channels, real provider replay verification or webhook signing.
- No cross-channel provenance, message embedding, LLM analysis or prompt-eval harness.
- No real financial attribution or real sampled QA labels.
- No tracing, metrics stack, alert/responder, deployment or rollback yet.
- No public online demo, signed-in real users, performance benchmark or third-party security audit.

See `docs/BACKLOG.md` for priorities and `docs/COURSE_MATRIX.md` for 2026 rubric gaps.
