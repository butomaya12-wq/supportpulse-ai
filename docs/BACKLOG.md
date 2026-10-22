# Implementation backlog — SupportPulse AI

Entries are planned GitHub issues. Not GitHub issues yet; this package is local and no remote repository has been created.

| ID | Priority | Deliverable / acceptance | State |
|---|---|---|---|
| SP-001 | P0 | New, independent public GitHub repo with source, README, AGENTS, clear synthetic/demo scope and tracked issues | BLOCKED: repo needs to be created |
| SP-002 | P0 | Docker Compose starts API + PostgreSQL locally; live connection smoke-verified | CODED / NOT EXECUTED IN DOCKER |
| SP-003 | P0 | Tenant-keyed persistence and fixture, repeatable schema migration/rollback | PARTIAL: model+fixture, migration missing |
| SP-004 | P0 | Import deduplication, schema validation, cursor + health; tests for idempotency and conflict | CODED; 14 LOCAL API TESTS PASSED |
| SP-005 | P0 | Verifiable cross-source timeline, identity link and provenance | PARTIAL: single source only |
| SP-006 | P0 | Deterministic overdue detector with insufficient-data refusal | CODED; 14 LOCAL API TESTS PASSED |
| SP-007 | P0 | Supervisor review, assignment and verified corrective action with audit | CODED; 14 LOCAL API TESTS PASSED |
| SP-008 | P0 | Overview API with meaningful denominators and null impact | CODED; 14 LOCAL API TESTS PASSED |
| SP-009 | P0 | Responsive dashboard with cases, evidence and review controls | CODED; BROWSER E2E NOT RUN |
| SP-010 | P1 | AI explicit-promise extraction with abstention + labeled eval harness | NOT STARTED |
| SP-011 | P0 | CI + UI/browser tests + PostgreSQL integration suite | PARTIAL: 14 API tests passed locally, CI only configured |
| SP-012 | P0 | Real hosted synthetic demo, secrets managed, rollback | NOT STARTED |
| SP-013 | P0 | Correlated logs/metrics/traces, user-impact alert, bounded on-call | NOT STARTED |
| SP-014 | P0 | Docs, demos and evidence for 12-course-criterion peer review | PARTIAL |
| SP-DISC-001 | P0 parallel | Five buyer interviews; compare installed CRM; validated data permissions | NOT STARTED |
| SP-DISC-002 | P0 parallel | Buyer budget, willingness to pay, business-level pilot success target | NOT STARTED |

## Stop conditions
Do not turn synthetic scaffolding into a real business deployment before authentication, migrations, retention, tenant isolation, security, observability and consent/permissions review. Do not claim a solved market problem until buyer discovery provides evidence.
