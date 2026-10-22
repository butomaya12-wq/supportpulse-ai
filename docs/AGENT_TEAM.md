# AI-assisted engineering team and human ownership

This is a **process specification**, not proof that several autonomous agents have executed tasks independently.

| Role | Responsibility | Output | Escalation |
|---|---|---|---|
| Human Product Owner | Approves use cases, spending, buyer access, production releases and market claims | Scope decision, signed-off acceptance | Always owns real data or business commitment |
| Orchestrator / AI engineer | Splits bounded story into tracked acceptance-driven tasks, reconciles status | Design, issue plan, implementation trace | Cannot self-approve production, credentials, or business evidence |
| Implementer | Writes isolated code/config against approved scope | PR with tests and migration impact | Stops if tests contradict spec |
| QA / Evidence reviewer | Runs test matrix, checks negative paths and actual outputs | PASS/FAIL record with reproducible commands | Can block release |
| Security / Data reviewer | Reviews auth boundaries, privacy, attribution, fairness and telemetry | Risk ledger, hardening requirements | Must reject use of live conversations in synthetic demo |
| Course reviewer | Independently audits 12 rubric criteria against artifacts | Honest scores and missing-evidence list | Cannot convert design docs into fake runtime evidence |

**Workflow:** User problem -> falsifiable hypothesis -> approved spec -> coding -> negative/integration tests -> QA/Red-team -> human release decision -> observation. Agent decisions are documented in commits/issues; no model's self-report counts as runtime proof.

**Iteration 001 evidence:** authored files and local Python/HTTP tests. GitHub issue discussion, PR review, browser E2E, Postgres runtime, agent-alert testing and real customer feedback are NOT verified.
