# Iteration 007B — agent repairs a strictly bounded synthetic overview incident

## Objective and honesty boundary

The [AI Dev Tools Zoomcamp 2026 Project 2 rubric](https://github.com/DataTalksClub/ai-dev-tools-zoomcamp/blob/main/project/README.md) requires an on-call agent that **wakes up on an alert and fixes the issue**. This extension makes a fix possible, but **only for an explicitly armed synthetic dashboard gate**, not general production failures. It does NOT fix arbitrary server crashes, broken database queries or real customer problems, and does NOT use an LLM.

**Do not claim 2/2 until a real Grafana webhook triggers actual agent repair on the owner's Mac and the before/after evidence is captured.**

## Causal evidence and safety design

- The optional `compose.repair.yaml` overlay enables `SP_REPAIR_DRILL_ENABLED=1` and a private strong repair token on `web` and `oncall` only; disabled in all other deployments.
- A **second independent secret** `SP_REPAIR_TOKEN` is created in the same gitignored `.env.oncall` file. Grafana knows only the existing webhook credential; only web and oncall receive the separate repair credential. Neither secret is printed or checked into git. Token comparison is constant-time and intent headers are mandatory.
- Operator explicitly arms **one synthetic failure** using `POST /api/v1/demo/repair-drill/arm`. A 10-minute in-memory maximum lifetime and restart safety bound its impact. While broken, a **normal supervisor request** `GET /api/v1/overview` returns 503; `/health` stays healthy. Business PostgreSQL, customer cases, accounts, services, source records and actual commitments are not altered.
- Real Grafana 5xx metric alert sends a scoped, Bearer-authenticated webhook.
- The agent **probes ordinary overview and /health**. Only if overview is 503 AND health is 200 does it fetch its dedicated `state` endpoint and require `state=BROKEN`, `data_mode=SYNTHETIC_ONLY`, and a valid integer revision.
- The only allowed mutating action is `POST /api/v1/demo/repair-drill/repair?expected_revision=N`, using the private token + exact intent header. Backend uses lock + revision compare-and-swap, never a generic shell/database/deployment operation.
- Agent verifies the repair acknowledgment, exact revision, new state READY and **a fresh ordinary HTTP 200 response** before recording `AUTO_REPAIRED_SYNTHETIC` with `post_repair_http=200`. Its audit records **pre_repair** overview HTTP 503, **post_repair** 200, repair revision and explicit action `REPAIR_SYNTHETIC_OVERVIEW_GATE`.
- Successful repair **does not** claim the alert is resolved yet. Agent waits for a real Grafana `resolved` webhook with a second successful probe before persisting `VERIFIED_RESOLVED`. Metric window lag (up to approximately 2min) is expected.
- Every webhook deduplicated using stable fingerprint/start/state and persisted in private oncall SQLite, without raw alert content, tokens or customer IDs.
- Legacy header-scoped fault demonstration continues to work, but a plain overview remains 200, so it **cannot cause unintended agent repair**.
- Unknown alert, no latch, absent/expired revision, invalid token, failed post-repair probe → do not claim successful repair. **If the incident automatically expires before agent acts, that is not a credited agent fix.**

## Start on owner's Mac — preserve all existing volumes and host mappings

From the current `supportpulse-ai` directory, **generate the independent repair secret once**. Do not overwrite your existing webhook credential:

```bash
python3 - <<'PY'
from pathlib import Path
import os, secrets
path = Path(".env.oncall")
if not path.exists():
    raise SystemExit("Missing .env.oncall: keep the original Grafana webhook secret")
content = path.read_text()
if any(line.startswith("SP_REPAIR_TOKEN=") for line in content.splitlines()):
    print("Separate repair secret already exists; unchanged.")
else:
    with path.open("a") as out:
        out.write("SP_REPAIR_TOKEN=" + secrets.token_hex(32) + "\n")
    os.chmod(path, 0o600)
    print("Separate repair secret created locally, without printing it.")
PY
```

Then start all five overlays:

```bash
git pull --ff-only
docker compose --env-file .env.oncall \
  -f compose.yaml \
  -f compose.telemetry.yaml \
  -f compose.alerts.yaml \
  -f compose.oncall.yaml \
  -f compose.repair.yaml up --build -d
docker compose --env-file .env.oncall \
  -f compose.yaml -f compose.telemetry.yaml -f compose.alerts.yaml \
  -f compose.oncall.yaml -f compose.repair.yaml ps
```

**Do not delete or recreate `.env.oncall`**. Never paste either secret into ChatGPT. Do not run `down -v`. Keep owner's uncommitted `compose.yaml` Mac port override to `127.0.0.1:18080:8000`.

## Real runtime acceptance

1. Confirm four services healthy (PostgreSQL, web, Grafana, oncall) and Grafana Alerting → rule `SupportPulse: critical overview returns HTTP 5xx` is Normal, recipient `supportpulse-local-oncall` provisioned.
2. Check ordinary supervisor overview before arming = HTTP 200.
3. Load **repair** token into shell (never display it or print it in output):

```bash
set -a
source .env.oncall
set +a
```

4. Arm **only once**, after confirming rule is Normal and ready:

```bash
curl -sS -X POST \
 -H "Authorization: Bearer ${SP_REPAIR_TOKEN}" \
 -H 'X-SupportPulse-Repair-Drill: arm' \
 http://127.0.0.1:18080/api/v1/demo/repair-drill/arm
```

5. Generate real dashboard traffic to produce 503 counters. Monitor while the Grafana alert fires. A bounded 12-request script:

```bash
for i in {1..12}; do
  curl -sS -o /dev/null -w 'overview_http=%{http_code}\n' \
    -H 'Authorization: Bearer dev-only-supervisor-token' \
    http://127.0.0.1:18080/api/v1/overview
  sleep 2
done
```

The first requests should show **503**. After agent's repair, subsequent responses should become **200**. Do not interpret a 200 only after the 10-minute TTL as an agent fix.

6. Inspect authenticated oncall audit (token stays in shell, not copied into the chat):

```bash
curl -sS -H "Authorization: Bearer ${SP_ONCALL_WEBHOOK_TOKEN}" \
 http://127.0.0.1:18081/events
```

**Passing firing event:** `alert_status=firing`, `outcome=AUTO_REPAIRED_SYNTHETIC`, `action=REPAIR_SYNTHETIC_OVERVIEW_GATE`, `overview_http=503`, `post_repair_http=200`, `repair_revision=N`, `verified_recovery=0`.

**Passing resolved event** (once metrics window clears): `alert_status=resolved`, `outcome=VERIFIED_RESOLVED`, `health_http=200`, `overview_http=200`, `verified_recovery=1`.

7. In Grafana → Alerting → Alert rules → History, verify **Alerting → Normal** and contact's delivery succeeded. Save redacted screenshot and synthetic audit records as reviewer-accessible evidence.
8. Finally confirm business cases still exist in UI and PostgreSQL was not reset.

## If auto-fix fails

The fault will expire automatically after **at most 10 minutes** or on web container restart. This is a **safety fallback, not valid evidence of agent repair**. Do not repeatedly arm. Inspect oncall audit for `REPAIR_REJECTED`, `REPAIR_UNVERIFIED`, `INVESTIGATE_OVERVIEW_FAILURE` and diagnose exact rule delivery without revealing the secret. No real code changes, database repair or container restarts should be made by the agent.

## Engineering evidence

Automated tests check: no opt-in, secret/intent guard, bounded TTL, revision CAS, duplicate webhook idempotence, before 503 → agent repair → after 200 → resolved verified, unchanged business DB, no repair of unproven errors, Compose configuration and existing tests. Live Grafana/Mac evidence remains required independently of CI.

**Production-ready remains NO.** This is controlled synthetic failure repair demonstrating guardrails; we must still build real integrations, auth/privacy, external deployment and appropriate release controls before any pilot.
