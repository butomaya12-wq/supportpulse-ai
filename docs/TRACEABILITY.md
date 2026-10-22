# Implementation evidence — local iteration 001

Designed in `SCENARIO_SPEC_v0.2.md`. No external customer evidence or production access.

| AC | Current test/evidence | Status |
|---|---|---|
| AC-01 Idempotent events/commitment | `test_reimport_idempotent`, `test_immutable_provider_events` | LOCAL PYTEST PASS |
| AC-02 Timezone | Fixture Moscow + UTC, `test_naive_timestamps_and_watermark_regression_rejected` | LOCAL PYTEST PASS for aware timestamps; DST examples remain |
| AC-03 Candidate overdue with proof | `test_seed_and_full_human_workflow` | LOCAL PYTEST PASS |
| AC-04 Insufficient sync != violation | `test_missing_watermark_protects_manager`, `test_degraded_source_does_not_accuse` | LOCAL PYTEST PASS |
| AC-05 Second linked channel, verified identity | none | NOT DONE |
| AC-06 Vague/injected prompts | no LLM in release | NOT DONE |
| AC-07 Human review -> task -> audit | `test_seed_and_full_human_workflow` | LOCAL PYTEST PASS |
| AC-08 No evidence -> no verification | `test_seed_and_full_human_workflow` | LOCAL PYTEST PASS for missing proof and bounce; live event signing pending |
| AC-09 Late arrival revision/audit | evaluate transition and `test_seed_and_full_human_workflow` | PARTIAL |
| AC-10 Tenant scope | `test_cross_tenant_case_not_exposed` | LOCAL PYTEST PASS |
| AC-11 Unknown economics / ratio | `test_on_time_evidence_prevents_false_alert` and empty overview | PARTIAL |
| AC-12 One-command E2E | Compose exists; no Docker run yet | NOT VERIFIED |
| AC-13 Operational user-impact alert | none | NOT DONE |
| AC-14 Bounded on-call | none | NOT DONE |

### Iteration 001 validation (22 October 2026)

- `pytest -q` -> **14 passed** (Python 3.13 / SQLite in-memory TestClient).
- `python -m compileall -q app tests` -> PASS.
- `node --check app/static/ui.js` -> PASS.
- Uvicorn `/health` HTTP smoke -> **200**, `production_ready=false`.
- Browser code rendering snapshot created separately via injected synthetic DOM; NOT a browser E2E validation.
- Docker Compose/PostgreSQL E2E -> **NOT RUN** (Docker unavailable).
- CI GitHub workflow -> **NOT RUN** (GitHub repository not created).
