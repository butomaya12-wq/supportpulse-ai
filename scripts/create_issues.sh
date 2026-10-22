#!/usr/bin/env bash
set -euo pipefail
repo="butomaya12-wq/supportpulse-ai"
if ! command -v gh >/dev/null 2>&1; then echo 'Install GitHub CLI and authenticate with gh auth login'; exit 1; fi
if ! gh repo view "$repo" >/dev/null 2>&1; then echo "Create https://github.com/new repository supportpulse-ai first"; exit 1; fi
# Minimal set; full epic breakdown and acceptance criteria live in docs/BACKLOG.md.
while IFS='|' read -r title description; do
  [[ "$title" == \#* || -z "$title" ]] && continue
  if gh issue list --repo "$repo" --state all --limit 200 --json title --jq '.[].title' | grep -Fxq "$title"; then
    echo "Skip existing $title"; continue
  fi
  gh issue create --repo "$repo" --title "$title" --body "$description"
done <<'ISSUES'
# title|description
SP-001 Repo and project acceptance map|Verify README, AGENTS.md, docs/COURSE_MATRIX.md and published source; no edits to HandoffGuard.
SP-002 Docker Compose PostgreSQL smoke|Demonstrate docker compose up --build and import -> overview on PostgreSQL, capture reproducible evidence.
SP-003 Schema migrations|Implement migrations, rollback and tenant-sensitive integrity tests; startup create_all only for local demo.
SP-004 Safe ingestion|Verify deduplication, conflicting provider IDs rejected, monotonic source watermarks and failure modes.
SP-005 Identity and timeline provenance|Build verified cross-source identity linkage, no fuzzy automatic merge and immutable event references.
SP-006 Overdue evaluation|Deterministic rules and negative tests for missing source coverage, DST and bounced messages.
SP-007 Review workflow and audit|Role-gated human review, assign, evidence-based completion and append-only audit tests.
SP-008 KPI quality and denominators|Cohort-defined rates with null unknowns; no fabricated financial impact.
SP-009 Frontend quality and browser tests|Responsive dashboard, evidence cards, screen reader labels, client tests and user task success.
SP-010 AI abstention and evaluation|Explicit promise extraction with human approval, injection resistance and labeled evaluation; no auto sanctions.
SP-011 Reliable CI/integration|Postgres integration tests, browser E2E, synthetic fixtures, action checks on PR.
SP-012 Synthetic cloud demo and rollback|Safe public synthetic demo behind strong real auth, deploy and documented rollback path.
SP-013 Observability and bounded responder|Correlated logs/metrics/traces, real user-impact alert and bounded read-only on-call test.
SP-014 Peer-review evidence and release docs|English course spec, demos, reproducible commands, honest proof for each graded criterion.
SP-DISC-001 Five buyer interviews|Interview five independent buyer profiles, capture consent and last verified missed follow-up case.
SP-DISC-002 Paid pilot value validation|Validate decision owner, feasible data access, paid-pilot budget and measurable baseline.
ISSUES
