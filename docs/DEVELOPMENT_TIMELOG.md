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
