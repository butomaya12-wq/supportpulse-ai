# SupportPulse AI — development time ledger

**Purpose:** record the calendar span AND credible hands-on work time for the DataTalks.Club AI Dev Tools Zoomcamp 2026 **Project 2** submission. The course submission form asks for **"Time spent on project (hours)"**. Do not equate wall-clock elapsed time with actual working hours.

## Baselines (UTC)

| Event | Timestamp (UTC) | Evidence | Interpretation |
|---|---|---|---|
| First saved product-discovery blueprint artifact | 2026-10-22 18:14:27 | User's saved `SupportPulse_AI_Product_Discovery_Blueprint_v0.1.md` created-at metadata | Planning artifact timestamp; not exact moment thinking started |
| Engineering start mentioned during session | 2026-10-22 19:49:40 | Conversation timeline, retrospectively recovered 2026-10-23 | **Provisional start marker** for building the application; not a verified stopwatch reading |
| Initial remote GitHub commit authored | 2026-10-22 20:36:26 | GitHub `842752292c4a5ce5ebc07df3500ea6e42bd92005` commit authored timestamp (committed/pushed near 20:40:16) | Independent verifiable code milestone |
| Iteration 002 merged | 2026-10-23 07:26:20 | GitHub `6ff30c83d6033fca093435c3e2dbd10a24dfac67` | Verification UX / PostgreSQL tests |
| Iteration 003 merged | 2026-10-23 08:58:47 | GitHub `643436dc414c44c2e96a1f79f2054c8f6316eb82` | Browser E2E |
| Iteration 004 merged | 2026-10-23 14:08:39 | GitHub `0f7fd10d97dfc6278a0bb97dac02704558fb629f` | Guarded promise proposals / synthetic model mocks |
| Iteration 005 observability merged | 2026-10-23 18:09:53 | GitHub `c5142b2758f29c97b3f59084af9e2e70d6b78c28` | OpenTelemetry instrumentation and optional local Grafana overlay; Grafana UI proof still pending |

## Current snapshot

- **Measured at:** **2026-10-23 17:49:19 UTC** (= **2026-10-23 22:49:19 UTC+05:00**). Snapshot taken from the user-local time service.
- **Calendar elapsed from provisional engineering start:** **21 h 59 min 39 sec**.
- **Calendar elapsed from first published code commit:** **21 h 12 min 53 sec**.
- **Calendar elapsed from initial saved blueprint artifact:** **23 h 34 min 52 sec**.
- **Active hands-on hours:** **UNKNOWN — do not enter 22 hours into the course form.**
- **Release/completion time:** **NOT YET REACHED**. The course's deployment, CD, observability, impact alert, and alert-driven responder are missing; Project 2 peer reviews/submission are not evidenced.
- **Project 2 official page:** https://courses.datatalks.club/ai-dev-tools-2026/project/project2
- **Course official spec:** https://github.com/DataTalksClub/ai-dev-tools-zoomcamp/blob/main/project/README.md

## Session evidence (DO NOT add overlapping windows as work time)

| Session | Observation | Work time that can be counted |
|---|---|---|
| 2026-10-22 | Engineering marker 19:49:40 UTC; session recorded as ending 22:02:21 UTC (2 h 12 min 41 sec elapsed including possible idle) | **Unconfirmed**, may count only after user explicitly confirms uninterrupted work |
| 2026-10-23 | Earlier session resumed around 05:37:54 UTC; 004 accepted in local browser later that day; there were breaks and unknown idle intervals | **Unknown**, must not convert full span into continuous work hours |

## Forward-looking timekeeping procedure

At the start of a new engineering session, explicitly log a start timestamp; at the end, explicitly log a stop timestamp. Attribute interruptions/breaks as excluded time, record the issue or PR, and calculate **active work duration** from non-overlapping confirmed sessions. The assistant cannot keep a live stopwatch running in the background between messages. Update this ledger whenever a new confirmed session or milestone is recorded.

Proposed table for future sessions:

| UTC start | UTC stop | Breaks (min) | Net active hours | Work / evidence | Confirmation |
|---|---|---|---|---|---|
| Not yet tracked | — | — | — | — | — |

**Submission rule:** use only confirmed net working hours for the course field. For narrative write-ups, it is acceptable to report the clearly labeled calendar elapsed span since engineering start. These are different measurements.

## Observed assistant-led engineering session: iteration 005

- **Session started:** 2026-10-23 **17:56:49 UTC** (22:56:49 at UTC+05), source: user-local time service reading during session.
- **Snapshot after merging:** 2026-10-23 **18:10:01 UTC** (23:10:01 at UTC+05), source: user-local time service reading.
- **Elapsed session window:** **13 min 12 sec**. This includes tool execution and any idle time; **not equivalent to user's active hands-on hours**.
- **Deliverables:** PR #13, correlated request tracing/logging/metrics, 34 Python tests, 3 browser E2E, Docker CI, optional Grafana overlay.
- **Human active work time:** **UNKNOWN**; no user stopwatch / confirmed break report.
- **Next milestone:** actual Grafana UI proof and a new timestamped owner-local review session.


## Iteration 006 — user-impact alert

- **Scope:** Grafana-managed Prometheus alert for 5xx on critical `GET /api/v1/overview`, optional synthetic-only fault probe, and Normal → Firing → Normal operator runbook.
- **Merge timestamp:** 2026-10-23 **21:13:57 UTC** (2026-10-24 02:13:57 UTC+05); commit `fe71f0a9d55d532f63a30fbb85f9c564abcd9f92`. **Independent GitHub evidence.**
- **Post-merge CI:** [run 40025237221](https://github.com/butomaya12-wq/supportpulse-ai/actions/runs/40025237221), 4/4 green including 39 Python tests, PostgreSQL, three Chromium E2E and Docker.
- **Session wall-time window:** user requested start of this iteration at about **2026-10-24 02:06 UTC+05** (rounded, from conversation timestamp); current checkpoint **02:15:24 UTC+05** from user-local time service. Approx. **9 minutes** of elapsed elapsed wall-clock since this marker. This is not measured active human work time; do not submit it as worked hours.
- **User-local runtime Grafana alert proof:** **PENDING** (configuration and CI done, rule firing not yet observed). Completion timestamp not fixed until actual UI proof.
- **Active hands-on work hours:** **UNKNOWN**, pending explicit non-overlapping work sessions and break confirmation. Do not add assistant/tool runtime and human work hours together.


## Iteration 007 — bounded on-call webhook implementation

- **Owner request / session marker:** 2026-10-24 approx. **19:18 UTC+05** (per conversation-local clock). This is a start checkpoint, **not a verified stopwatch**.
- **Code merge:** 2026-10-24 **19:32:04 UTC+05** (2026-10-24 14:32:04 UTC); independent GitHub commit `149058afb4a06b2c83ab7e68309890f7df696a57` via PR #17.
- **Snapshot:** 2026-10-24 **19:32:17 UTC+05**, from user-local time service; about **14 min** calendar elapsed since the approximate request marker.
- **Deliverables:** guarded Grafana contact point, local webhook receiver, strict alert scope, read-only diagnostics, replay-safe private SQLite audit, synthetic-only Compose overlay, 56 Python tests, 3 Chromium E2E; post-merge main CI 4/4 PASS.
- **Local Grafana-to-webhook proof:** **PENDING**; does not count as a completed live on-call operation.
- **Human net working hours:** **UNKNOWN**. Tool execution is not necessarily owner hands-on time. Do not add this to course worked hours without user confirmation.


### Iteration 007 runtime evidence: real Grafana webhook

- **2026-10-24 15:24:51 UTC**: local oncall audit received actual Grafana `firing` event; result `ALERT_ACTIVE_PROBE_HEALTHY`; both read-only health/overview requests HTTP 200; recovery **not** claimed.
- **2026-10-24 15:27:50 UTC**: Grafana delivered `resolved`; agent performed both read-only probes (200/200), persisted `VERIFIED_RESOLVED` in separate oncall SQLite audit.
- **Verification:** owner retrieved event ledger via authenticated localhost `GET /events`, response HTTP 200. Synthetic-only; no customer data or autonomous repair.
- These event timestamps measure a **2 min 59 sec automated alert lifecycle**, NOT the total project duration, net human work hours, or time the assistant was actively coding. Those remain separate.
- **Course rubric:** on-call 0/2 pending actual safe repair. No course submission claimed.


### Iteration 007B — actual repair implementation milestone

- **2026-10-24 15:48:22 UTC** (= **20:48:22 UTC+05**): [PR #18](https://github.com/butomaya12-wq/supportpulse-ai/pull/18) merged, immutable commit `747964932044e43b8ca9e0cfc979c98b196535e2`. Independent GitHub timestamp.
- **2026-10-24 20:48:30 UTC+05**: current-time snapshot via user-local time service (8 seconds after merge).
- **Deliverables:** opt-in fail latch on normal overview, 10-minute safety expiry, separate repair secret, exact revision-scoped repair, before/after verification, oncall audit migration, 61 Python tests and existing E2E/PostgreSQL/Docker checks.
- **Real Mac repair evidence:** PENDING. Code completion is not proof of a Grafana-triggered repair; release not completed.
- **Human active project hours:** UNKNOWN because no independent hands-on stopwatch/break record for this interval. **Do not count wall-clock model/tool execution as user billable work.**


### Iteration 007B owner acceptance: autonomous synthetic repair

- **2026-10-24 17:03:51.130247 UTC** (= **22:03:51.130247 UTC+05**): incoming **real Grafana firing** webhook, oncall audit #3. Agent performed allowlisted `REPAIR_SYNTHETIC_OVERVIEW_GATE`: ordinary overview **503** before, **200** afterward; revision **1**; persisted `AUTO_REPAIRED_SYNTHETIC`. Separate confirmation by Grafana remained pending at this instant.
- **2026-10-24 17:06:51.927989 UTC** (= **22:06:51.927989 UTC+05**): genuine Grafana **resolved** webhook, oncall audit #4; two read-only health checks **200/200**; `VERIFIED_RESOLVED`.
- **Owner verification:** protected repair-drill state **READY**, revision 1, ttl 0, after the repair; 12 ordinary overview requests **503 × 6 then 200 × 6**.
- **Artifact:** [evidence record](EVIDENCE_ONCALL_REPAIR_2026-10-24.md). **Course estimate: On-call 2/2 provisional; 20/24 overall provisional** (human reviewer not yet evaluated).
- **Measured automated alert lifecycle:** 3 minutes 0.798 seconds between the two webhook *receipt* timestamps. This is **not agent repair latency**, since exact time the repair completed inside firing handler was not recorded separately, nor is this user working time.
- **Net human active hours:** **UNKNOWN**. The automated incident elapsed interval must not be treated as worked time; no complete stopwatch or breaks were captured.
- **Still missing:** separate Grafana Rule History screenshot for this repair trial and independent DB row-level non-mutation evidence.


### Iteration 008 — public reviewer deployment and verified auto-CD

- **2026-10-24 19:03:12 UTC**: [PR #20](https://github.com/butomaya12-wq/supportpulse-ai/pull/20) read-only public reviewer preview merged into `main` as `d38d753d0cdc671f0ffa52a204efb87895a017c2`. Includes two synthetic source-linked cases, strict zero-credential static bundle, Python build validation, and Chromium navigation/no-API tests.
- **2026-10-24 19:03:28–19:03:59 UTC**: Render created static service `supportpulse-ai-review-demo`, initial deploy `dep-dbeg2067bikc738b6t1g` status **LIVE**. This is a public static FRONTEND, not FastAPI/PostgreSQL or production system.
- **2026-10-24 19:06:43–19:07:07 UTC**: Render automatically deployed README/main commit `6d87306` (`dep-dbeg3gs9v7es73cg4gr0`, `trigger=new_commit`, **LIVE**). This confirms functioning auto-CD, but not CI-gated stages/manual prod release.
- **2026-10-24 19:08:09 UTC**: [independent GitHub Actions HTTPS smoke](https://github.com/butomaya12-wq/supportpulse-ai/actions/runs/40123896342) **PASS**, fetching public HTML and two immutable synthetic case records from `https://supportpulse-ai-review-demo.onrender.com`.
- **Course estimate:** Deployment 2/2 and CI/CD 2/3, **both provisional**: deployment is a reviewer frontend only, graders may demand a hosted working API; CI-gated dev → human-gated prod and rollback are not implemented. Total **23/24 provisional** pending human review.
- **Human working time:** still **UNKNOWN**. Render/GitHub timestamps prove separate milestones and automation duration, **not** net time actively worked by the owner.
