# DataTalks.Club AI Dev Tools Zoomcamp 2026 — Project 2: evidence audit

**Audited:** 2026-10-24. This document supersedes the original 2026-10-22 pre-deployment estimate.
**Official criteria:** https://github.com/DataTalksClub/ai-dev-tools-zoomcamp/blob/main/project/README.md
**Submission:** https://courses.datatalks.club/ai-dev-tools-2026/project/project2

## Provisional rubric scoring

This is an **assistant's evidence-based estimate**, NOT a reviewer-assigned score or course pass. The course requires **10/24 points AND 3 peer reviews**. Actual submission and peer reviews have not been confirmed.

| # | Criterion (maximum) | Provisional | Concrete evidence / gap |
|---|---|---:|---|
| 1 | Problem Description (2) | **2** | [README](../README.md) documents broken customer promises, expected lifecycle, limitations and synthetic scope |
| 2 | Product Specification (2) | **2** | [Scenario spec](SCENARIO_SPEC_v0.2.md), public GitHub issues with acceptance checks, PRs linked to issues |
| 3 | Agent Team Specification (2) | **2** | [Agent team](AGENT_TEAM.md) gives roles, process, human owner and escalation; it describes **process**, not autonomous agent execution |
| 4 | Context Management (2) | **2** | [AGENTS.md](../AGENTS.md) references modular spec/process/research documents |
| 5 | Application (2) | **2** | Local Mac browser owner walkthrough, FastAPI, PostgreSQL persistent Docker; verified case 1 & 2 |
| 6 | Testing (2) | **2** | Automated Python unit/API and isolated PostgreSQL integration and 3 Chromium E2E tests in [CI for code 0f7fd10](https://github.com/butomaya12-wq/supportpulse-ai/actions/runs/39967126823), **4/4 jobs PASS** |
| 7 | Containerization (2) | **2** | [compose.yaml](../compose.yaml) starts DB + web, owner reported both healthy locally, browser at `127.0.0.1:18080` (Mac-local port override) |
| 8 | Deployment (2) | **0** | No public reachable deployment of SupportPulse AI; localhost demo alone is not a verified hosted deployment |
| 9 | CI/CD (3) | **1** | GitHub Actions runs tests on PRs; **CD / dev + prod release / rollback are not implemented** |
| 10 | Observability (2) | **2 (provisional)** | Owner locally verified a key dashboard request: Tempo trace `GET /api/v1/overview` HTTP 200 with trace ID `2c250120628f398504f235b20b875b0e`, Loki `http.completed` with **exactly the same** ID, and Prometheus `supportpulse_http_requests_total` series. CI tests safe structured instrumentation. **Core multi-request business workflow still needs separate evidence; peer reviewer decides**. See [Issue #12](https://github.com/butomaya12-wq/supportpulse-ai/issues/12). |
| 11 | Alerting on User Impact (1) | **1 (provisional)** | [Grafana impact alert rule](../ops/grafana/alerting/overview-5xx.yaml) loaded in local Grafana. Owner generated **12/12 synthetic HTTP 503** and observed real state history **Alerting 2026-10-24 18:41:00 → Normal 18:43:10**. Critical supervisor overview route, static Prometheus 5xx labels. Ordinary HTTP 200 after drill and reviewer-accessible screenshot archiving still pending; [Issue #14](https://github.com/butomaya12-wq/supportpulse-ai/issues/14). |
| 12 | On-Call Agent (2) | **0** | Real Grafana firing and resolved webhooks received; read-only diagnostics and verification logged (2026-10-24). An actual repair by the responder is still missing, so official criterion remains 0/2. Issue #16. |

**Total provisional: 18/24**, subject to human peer-review scoring and evidence completeness.

**Course completion:** **NOT COMPLETE**, even though the provisional estimate exceeds the 10-point numerical threshold. It additionally requires **3 actual peer reviews, a submitted public repo and exact commit, project work hours**, and review outcome. Consult the course page for current deadlines.

## Highest-priority gaps for full rubric, not just passing score

1. Deploy a **clearly labeled synthetic-only** app to an accessible demo environment with suitably isolated credentials/storage; provide URL or a clear deployment demonstration. Do not expose demo bearer tokens publicly with real data.
2. Add safe staged release process (CI -> development CD -> human-gated release, rollback with smoke check); database migration and rollback discipline.
3. **Extend verified dashboard-level observability to the entire corrective workflow** (import -> candidate -> supervisor confirmation -> correction), documenting each request trace and audit transition. The currently verified Tempo/Loki/Prometheus proof covers one overview request only, not one continuous cross-request trace.
4. **Preserve alerting evidence for peer reviewers**: local Grafana History proves an explicitly injected synthetic supervisor overview HTTP 503 caused Alerting and subsequent Normal; archive the owner's proof, verify an ordinary HTTP 200 after the drill, and make the drill reproducible without exposing credentials.
5. Build a **bounded alert-driven on-call responder** in a disposable synthetic environment with an allowlisted safe fix, verification and explicit human approval for risky actions; demonstrate the entire alert -> agent -> fix cycle. Distinct from business-logic AI proposal generation.
6. Update English README/docs/architecture/traceability so reviewer sees **actual 2026-10-23 evidence**, not stale `NOT IMPLEMENTED` statements from iteration 001. Provide a single reproduction guide.
7. Submit [Project 2](https://courses.datatalks.club/ai-dev-tools-2026/project/project2) with the **public repository URL, immutable commit SHA and credible net project hours**, and complete **3 peer reviews**.

## Honest non-course constraints

The current app intentionally refuses production mode and has no authorized real customer integrations, real user privacy/consent program, production authentication, deployment migration strategy, real financial attribution or validated LLM extraction quality. **Full course points do not imply production readiness.** External OpenAI model adapter is implemented but not verified with live model calls. Business outcomes and recovered revenue remain UNKNOWN.

## Time account

See [DEVELOPMENT_TIMELOG.md](DEVELOPMENT_TIMELOG.md). On 2026-10-23 at 17:49:19 UTC, elapsed calendar time from the provisional engineering start was **21 h 59 min 39 sec**; this is **not hours worked**.
