# Iteration 007 — bounded synthetic Grafana on-call responder

This implementation connects a **real Grafana notification** from the provisioned critical overview alert to a separate on-call HTTP service.

**Do not claim on-call acceptance until a real Grafana Firing → on-call event → resolved notification is observed on the owner's Mac.** CI unit tests use synthetic webhook payloads and stubbed probes, not a live Grafana webhook.

## Exact capabilities and boundaries

- Authentication: Grafana webhook contact point uses a strong **private Bearer credential** through Grafana's secure `authorization_credentials` setting. The value is provisioned from the local `SP_ONCALL_WEBHOOK_TOKEN` environment variable. Never commit the secret or put it in screenshot/chat.
- Strict alert allowlist: title `SupportPulse: critical overview returns HTTP 5xx`, rule UID `sp_overview_5xx_v1` if sent, labels `project=supportpulse-ai`, `stage=synthetic-only`, `user_impact=critical-overview-read`, with a valid Grafana fingerprint and source timestamp.
- Fixed response action: **two read-only GET requests** — internal `http://web:8000/health` and internal `http://web:8000/api/v1/overview` without the fault-drill header. No arbitrary URL, shell, agent code execution, restart, DB write, outbound email, customer notification or AI-generated command.
- Decisions: `ALERT_ACTIVE_PROBE_HEALTHY` / `INVESTIGATE_OVERVIEW_FAILURE` / `ABSTAIN_INSUFFICIENT_HEALTH` for firing. **Only** a Grafana `resolved` notification plus **both** successful probes results in `VERIFIED_RESOLVED`.
- Replay safety: deduplicate by hashed Grafana alert fingerprint, normalized start time and status; duplicates **never** rerun diagnostics.
- Audit: sanitized SQLite in a *separate* named volume `oncall_audit`. It records no payload, message, token, customer ID, arbitrary annotations or raw alert fingerprint.
- This is a **deterministic, bounded runbook agent**, NOT an LLM/AI reasoning system. A genuine end-to-end safe remediation action beyond read-only diagnostics is not implemented. It must not receive full course on-call points without assessing the actual rubric and reviewer evidence.

## Mac startup, avoiding old data loss

This uses a fourth Docker Compose overlay. It does NOT change `compose.yaml` or the existing PostgreSQL volume or the Mac-local port 18080.

First generate a secret file once **locally**. Do not paste its contents into ChatGPT or GitHub:

```bash
python3 - <<'PY'
from pathlib import Path
import os
import secrets
path = Path(".env.oncall")
try:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
except FileExistsError:
    print("Existing .env.oncall reused; no key was overwritten.")
else:
    with os.fdopen(fd, "w", encoding="ascii") as out:
        out.write("SP_ONCALL_WEBHOOK_TOKEN=" + secrets.token_hex(32) + "\n")
    print("Local on-call secret generated (not printed).")
PY
```

`.env.oncall` is git-ignored. The secret must be consistent across Grafana and the on-call service, which Compose injects for both.

```bash
git pull --ff-only
docker compose --env-file .env.oncall \
  -f compose.yaml -f compose.telemetry.yaml -f compose.alerts.yaml -f compose.oncall.yaml config --quiet
docker compose --env-file .env.oncall \
  -f compose.yaml -f compose.telemetry.yaml -f compose.alerts.yaml -f compose.oncall.yaml up --build -d
docker compose --env-file .env.oncall \
  -f compose.yaml -f compose.telemetry.yaml -f compose.alerts.yaml -f compose.oncall.yaml ps
```

Expected: existing PostgreSQL healthy; web at 127.0.0.1:18080; Grafana 127.0.0.1:13000; new on-call at 127.0.0.1:18081. Grafana may need to restart/re-provision the contact point.

**Never** run `docker compose down -v` (would delete persistent data).

## Verify actual Grafana contact and on-call delivery

1. Open Grafana at `http://127.0.0.1:13000` → Alerting → Contact points. Confirm `supportpulse-local-oncall` exists and is a webhook contact. The authorization credential MUST remain masked; do not publish it.
2. Open Alert rules → `SupportPulse: critical overview returns HTTP 5xx`. Confirm the rule now uses this local contact point. It should normally be Normal.
3. Run the **same explicitly marked 503 drill** used in Iteration 006 (12 calls, two-second spacing). All 12 must return 503. Normal dashboard traffic (without drill header) must still return 200.
4. After Grafana History confirms Firing, request on-call sanitized audit on Mac **without displaying the secret**:

```bash
set -a
source .env.oncall
set +a
curl -fsS -H "Authorization: Bearer ${SP_ONCALL_WEBHOOK_TOKEN}" \
  http://127.0.0.1:18081/events
```

Expected: `alert_status: firing`, action `TWO_READ_ONLY_PROBES`, outcome `ALERT_ACTIVE_PROBE_HEALTHY` (ordinary overview succeeds). This is **detection and diagnosis, NOT automatic remediation**.

5. After stopping the 503 drill, Grafana should return Normal in around the configured two-minute window. Check audit again; a **separate** `resolved` event with `VERIFIED_RESOLVED` confirms actual delivery and safe verification. If the contact configuration fails to deliver, inspect the UI notification delivery history and `docker compose ... logs oncall --tail 50`. Do not describe a missing notification as a successful autonomous response.

6. Tests should show an unmarked overview is HTTP 200 and neither two existing synthetic cases nor PostgreSQL were modified.

## Security and known limitations

- **Local sandbox only**: default Grafana admin credentials, demo supervisor token, plaintext internal HTTP and non-TLS loopback bindings are NOT appropriate for production.
- The Bearer credential establishes possession but does **not** cryptographically bind the raw body. The receiver validates alert identifiers and persists deduplication, but an attacker who obtains the secret could forge a notification. Add Grafana HMAC and timestamp-based anti-replay before remote exposure.
- Grafana webhook retry intervals and resolved delivery depend on actual contact point policy; only owner-local observation verifies them.
- A firing alert cannot be marked recovered from probe success; the metric window may remain positive. Recovery requires real resolved webhook + successful probes.
- There is **no autonomous repair**. This first on-call version provides real alert intake, bounded diagnosis, abstention and verified recovery only. Risky remediation remains human-gated for future iteration.
- `oncall_audit` stores sanitized operational metadata only; it is not a cryptographically tamper-evident audit store.
- No public deployment, production authentication, real customer data or third-party paging.

## Evidence

- [Original Grafana 503 alert + operator runbook](ALERT_DRILL_RUNBOOK.md)
- [Project 2 course matrix](COURSE_MATRIX.md)
- [Source for real Grafana webhook integration](https://grafana.com/docs/grafana/latest/alerting/configure-notifications/manage-contact-points/integrations/webhook-notifier/)
- [Grafana contact point file-provisioning](https://grafana.com/docs/grafana/latest/alerting/set-up/provision-alerting-resources/file-provisioning/)
