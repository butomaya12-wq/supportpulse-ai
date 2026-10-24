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
| 8 | Deployment (2) | **2 (provisional)** | [Public HTTPS read-only reviewer demo](https://supportpulse-ai-review-demo.onrender.com) successfully published on Render as static site (initial deploy `dep-dbeg2067bikc738b6t1g`, commit `d38d753`). [External GitHub Actions HTTP smoke PASS](https://github.com/butomaya12-wq/supportpulse-ai/actions/runs/40123896342) confirmed published HTML and two synthetic case JSON records; Chromium CI validated navigable stages without any `/api/` requests. **This is a static client-side reviewer demo; FastAPI/PostgreSQL are NOT hosted or publicly available**, so peer reviewers may grade differently. [Deployment evidence](PUBLIC_PREVIEW_DEPLOYMENT.md). |
| 9 | CI/CD (3) | **2 (provisional)** | GitHub Actions runs tests on pull requests and `main`; connected Render public static demo now **auto-deploys after GitHub main commits**. Render actual deployment `dep-dbeg3gs9v7es73cg4gr0` (commit `6d87306`) finished `live` with trigger=`new_commit`, proving CD. Separate [GitHub Actions public HTTPS smoke](https://github.com/butomaya12-wq/supportpulse-ai/actions/runs/40123896342) PASS. **CI-gated dev CD and human-approved production releases/rollback are NOT implemented**; 3/3 is not claimed. |
| 10 | Observability (2) | **2 (provisional)** | Owner locally verified a key dashboard request: Tempo trace `GET /api/v1/overview` HTTP 200 with trace ID `2c250120628f398504f235b20b875b0e`, Loki `http.completed` with **exactly the same** ID, and Prometheus `supportpulse_http_requests_total` series. CI tests safe structured instrumentation. **Core multi-request business workflow still needs separate evidence; peer reviewer decides**. See [Issue #12](https://github.com/butomaya12-wq/supportpulse-ai/issues/12). |
| 11 | Alerting on User Impact (1) | **1 (provisional)** | [Grafana impact alert rule](../ops/grafana/alerting/overview-5xx.yaml) loaded in local Grafana. Owner generated **12/12 synthetic HTTP 503** and observed real state history **Alerting 2026-10-24 18:41:00 → Normal 18:43:10**. Critical supervisor overview route, static Prometheus 5xx labels. Ordinary HTTP 200 after drill and reviewer-accessible screenshot archiving still pending; [Issue #14](https://github.com/butomaya12-wq/supportpulse-ai/issues/14). |
| 12 | On-Call Agent (2) | **2 (provisional)** | On 2026-10-24 a real Grafana `firing` webhook triggered allowlisted synthetic repair: [owner on-call audit](EVIDENCE_ONCALL_REPAIR_2026-10-24.md) event #3 proves `overview_http=503`, `action=REPAIR_SYNTHETIC_OVERVIEW_GATE`, `post_repair_http=200`, `repair_revision=1`. A separate real `resolved` webhook event #4 reports `VERIFIED_RESOLVED`, probes 200/200. Owner confirmed secure drill `READY` rev 1; Grafana History screenshot for **this incident was provided by owner** (Alerting 22:03:50 → Normal 22:05:50); original PNGs still need committing for external reviewers (Issue #19). Independent business DB row-level nonmutation evidence still pending. Limited synthetic repair only; grading subject to reviewer. [Issue #16](https://github.com/butomaya12-wq/supportpulse-ai/issues/16). |

**Total provisional: 23/24**, subject to human peer-review scoring and evidence completeness.

**Course completion:** **NOT COMPLETE**, even though the provisional estimate exceeds the 10-point numerical threshold. It additionally requires **3 actual peer reviews, a submitted public repo and exact commit, project work hours**, and review outcome. Consult the course page for current deadlines.

## Highest-priority gaps for full rubric, not just passing score

1. **Current static demo is deployed and verified externally**, but the **real FastAPI/PostgreSQL backend is still local**. Build guarded staging for the real API with safe authentication/data isolation (see [Issue #21](https://github.com/butomaya12-wq/supportpulse-ai/issues/21)); never expose existing dev tokens.
2. Upgrade verified **Render static preview auto-CD** to the full three-point release model: CI-gated development deployment → human-approved production release → tested rollback/smoke and database migration discipline (see [Issue #21](https://github.com/butomaya12-wq/supportpulse-ai/issues/21)).
3. **Extend verified dashboard-level observability to the entire corrective workflow** (import -> candidate -> supervisor confirmation -> correction), documenting each request trace and audit transition. The currently verified Tempo/Loki/Prometheus proof covers one overview request only, not one continuous cross-request trace.
4. **Preserve alerting evidence for peer reviewers**: local Grafana History proves an explicitly injected synthetic supervisor overview HTTP 503 caused Alerting and subsequent Normal; archive the owner's proof, verify an ordinary HTTP 200 after the drill, and make the drill reproducible without exposing credentials.
5. **Publish the captured Grafana History and Instances screenshots** as repository-hosted artifacts for peer graders ([Issue #19](https://github.com/butomaya12-wq/supportpulse-ai/issues/19)); the already observed local alert → agent → repair → recovery sequence is documented in [the evidence record](EVIDENCE_ONCALL_REPAIR_2026-10-24.md). Broader production fault repair remains out of scope.
6. Update English README/docs/architecture/traceability so reviewer sees **actual 2026-10-23 evidence**, not stale `NOT IMPLEMENTED` statements from iteration 001. Provide a single reproduction guide.
7. Submit [Project 2](https://courses.datatalks.club/ai-dev-tools-2026/project/project2) with the **public repository URL, immutable commit SHA and credible net project hours**, and complete **3 peer reviews**.

## Honest non-course constraints

The current app intentionally refuses production mode and has no authorized real customer integrations, real user privacy/consent program, production authentication, deployment migration strategy, real financial attribution or validated LLM extraction quality. **Full course points do not imply production readiness.** External OpenAI model adapter is implemented but not verified with live model calls. Business outcomes and recovered revenue remain UNKNOWN.

## Time account

See [DEVELOPMENT_TIMELOG.md](DEVELOPMENT_TIMELOG.md). On 2026-10-23 at 17:49:19 UTC, elapsed calendar time from the provisional engineering start was **21 h 59 min 39 sec**; this is **not hours worked**.
