# Acceptance evidence: Grafana-triggered bounded synthetic repair

**Date:** 2026-10-24  
**Environment:** owner-operated Mac Docker Compose, four services, localhost only; `SP_MODE=synthetic_local` and fifth opt-in repair overlay.  
**Evidence source:** owner-provided Mac Terminal outputs and Grafana screenshot in the development conversation. These are **reported observations**, not independently accessed local host logs by an external reviewer.  
**Reproduction:** [on-call repair drill runbook](ONCALL_REPAIR_DRILL_v0.2.md), [code in PR #18](https://github.com/butomaya12-wq/supportpulse-ai/pull/18), [Issue #16](https://github.com/butomaya12-wq/supportpulse-ai/issues/16).

## Inputs and immutable acceptance checkpoints

1. Before arming: normal `GET /api/v1/overview` gave `HTTP 200`; protected drill state was `{"state":"READY","revision":0,"ttl_seconds":0,"data_mode":"SYNTHETIC_ONLY"}`; owner Grafana rule screenshot showed green `Normal`.
2. Owner armed **once** using private separate repair secret, and received:

   ```json
   {"state":"BROKEN","revision":1,"max_duration_seconds":600,"data_mode":"SYNTHETIC_ONLY"}
   ```
3. Owner sent **12 normal supervisor requests** (no special synthetic HTTP fault header; the ordinary critical route itself returned 503 while latch was active) at 2-second intervals. The exact response sequence was:

   ```text
   503 503 503 503 503 503 200 200 200 200 200 200
   ```

4. Owner fetched authenticated `http://127.0.0.1:18081/events`. Relevant newest sanitized records:

| Event ID | Received timestamp (UTC) | Alert | Outcome | Action | /health | Overview pre | Overview post | Revision | Verified Grafana resolution |
|---:|---|---|---|---|---:|---:|---:|---:|---:|
| 3 | 2026-10-24T17:03:51.130247Z | `firing` | `AUTO_REPAIRED_SYNTHETIC` | `REPAIR_SYNTHETIC_OVERVIEW_GATE` | 200 | **503** | **200** | **1** | 0 |
| 4 | 2026-10-24T17:06:51.927989Z | `resolved` | `VERIFIED_RESOLVED` | `TWO_READ_ONLY_PROBES` | 200 | 200 | not applicable | none | 1 |

The previous events #1-2 remained in the on-call audit, supporting audit persistence across the code upgrade; they concern an **earlier read-only diagnosis**, and should not be misrepresented as part of this repair experiment.

5. Owner inspected the separately authenticated state endpoint again. **Actual response:**

   ```json
   {"state":"READY","revision":1,"ttl_seconds":0,"data_mode":"SYNTHETIC_ONLY"}
   ```

## Why this is an agent-caused fix, not just alert self-resolution

- The test started with `BROKEN` revision **1**, and a normal protected business dashboard request actually returned HTTP 503. Unlike the previous header-only demonstration, the dashboard read itself was impaired on the synthetic local test environment.
- The `firing` event's persisted action is the specifically authorized **repair**, not merely read-only health diagnostics. Its audit reports pre-repair 503, post-repair 200, revision 1. Agent code performs protected state `BROKEN` lookup, fixed allowlisted repair call using revision compare-and-swap, subsequent state `READY` and overview GET 200 verification before persisting that outcome.
- The `resolved` event arrived **about 3 minutes later**, with both read-only probes 200 and `verified_recovery=1`. It is a separate Grafana notification, not fabricated by the agent's earlier attempt.
- The observed 503→200 sequence happened over approximately 24 seconds of manual probes, far earlier than the ten-minute maximum expiration safety bound.
- A matching **Grafana Alert Rule → History screenshot from this second (repair) trial remains to be attached**; true notification delivery is independently reflected by two stored webhook events, but reviewers may require screenshots of the UI.

## Guardrails and course-scoring boundaries

- [x] Alert-driven responder woke up on a **real Grafana-to-oncall webhook**.
- [x] Deterministic, bounded responder performed a **real state transition** in an isolated synthetic subsystem, and verified the same route recovered.
- [x] Separate secret for repair, explicit action header, revision check, ten-minute safety TTL, no arbitrary shell/restart/deploy allowed by repair code.
- [x] Post-recovery `resolved` webhook and fresh 200/200 diagnostics saved in the on-call event ledger.
- [ ] Reviewer-accessible screenshot from Grafana History for **this exact repair trial** (owner's existing first alert test screenshot is from a different earlier drill).
- [ ] Independent comparison of every business PostgreSQL row before/after this particular test. CI separately asserts the repair endpoints do not alter the sampled business model tables, and the original DB container was not recreated, but that's not an exact row-level runtime proof.
- [ ] No public production deployment, real customer data, dynamic on-call remediation beyond the explicit allowlist, or live LLM planning. This demo **does not establish production readiness**.

**Rubric interpretation:** official Project 2 on-call rubric awards 2 points for `An agent wakes up on an alert and fixes the issue.` These observations support **provisional 2/2** for a specifically bounded synthetic scenario. Final review score remains for course peer graders. See [current course audit](COURSE_MATRIX.md).
