"""Synthetic-only bounded on-call responder: read-only diagnostics, no business writes.

Incoming Grafana payloads are untrusted even after Bearer authentication. Only a
single named/allowlisted synthetic alert is accepted. No LLM, shell, restart, SQL
mutation, unbounded URL fetch, deployment or customer contact is possible.
"""
import hashlib
import os
import re
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ALERT_NAME = "SupportPulse: critical overview returns HTTP 5xx"
ALERT_UID = "sp_overview_5xx_v1"
LABELS = {
    "project": "supportpulse-ai",
    "stage": "synthetic-only",
    "user_impact": "critical-overview-read",
}
lock = threading.RLock()


def db_path() -> Path:
    return Path(os.environ.get("SP_ONCALL_DB", "/data/oncall.sqlite3"))


def init_store() -> None:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path, timeout=5) as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS agent_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            received_utc TEXT NOT NULL,
            fingerprint_hash TEXT NOT NULL,
            starts_at TEXT NOT NULL,
            alert_status TEXT NOT NULL,
            outcome TEXT NOT NULL,
            action TEXT NOT NULL,
            health_http INTEGER NOT NULL,
            overview_http INTEGER NOT NULL,
            verified_recovery INTEGER NOT NULL,
            UNIQUE(fingerprint_hash, starts_at, alert_status)
        )""")
        conn.commit()


def _checked_alert(payload: dict) -> tuple[str, str, str]:
    """Return (status, hashed fingerprint, normalized start); fail closed."""
    if not isinstance(payload, dict):
        raise ValueError("NOT_AN_OBJECT")
    status = payload.get("status")
    alerts = payload.get("alerts")
    if status not in {"firing", "resolved"} or not isinstance(alerts, list) or len(alerts) != 1:
        raise ValueError("BAD_NOTIFICATION_ENVELOPE")
    alert = alerts[0]
    if not isinstance(alert, dict) or alert.get("status") != status:
        raise ValueError("INCONSISTENT_ALERT_STATUS")
    labels = alert.get("labels")
    if not isinstance(labels, dict) or labels.get("alertname") != ALERT_NAME:
        raise ValueError("UNKNOWN_ALERT")
    if any(labels.get(k) != v for k, v in LABELS.items()):
        raise ValueError("UNKNOWN_ALERT_SCOPE")
    if labels.get("__alert_rule_uid__", ALERT_UID) != ALERT_UID:
        raise ValueError("UNKNOWN_RULE_UID")
    fingerprint = alert.get("fingerprint")
    if not isinstance(fingerprint, str) or not re.fullmatch(r"[0-9a-fA-F]{8,64}", fingerprint):
        raise ValueError("BAD_FINGERPRINT")
    start = alert.get("startsAt")
    if not isinstance(start, str):
        raise ValueError("BAD_ALERT_TIMESTAMP")
    try:
        parsed = datetime.fromisoformat(start.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("BAD_ALERT_TIMESTAMP") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("BAD_ALERT_TIMESTAMP")
    # The timestamp helps group retries; it is not authentication.
    key = hashlib.sha256(fingerprint.lower().encode("ascii")).hexdigest()[:24]
    return status, key, parsed.astimezone(timezone.utc).isoformat()


def _target_url(path: str) -> str:
    """Fixed, internal service allowlist — no URL from a Grafana payload."""
    base = os.environ.get("SP_ONCALL_TARGET", "http://web:8000")
    u = urlparse(base)
    if (u.scheme != "http" or u.hostname not in {"web", "127.0.0.1", "localhost"}
            or u.port not in {8000, 18080} or u.path not in {"", "/"}
            or u.query or u.fragment or u.username or u.password):
        raise RuntimeError("ONCALL_TARGET_NOT_ALLOWLISTED")
    return base.rstrip("/") + path


def _http_probe(path: str, authenticated: bool = False) -> int:
    headers = {}
    if authenticated:
        token = os.environ.get("SP_SUPERVISOR_TOKEN", "")
        if not token:
            return 0
        headers["Authorization"] = "Bearer " + token
    request = Request(_target_url(path), headers=headers, method="GET")
    try:
        with urlopen(request, timeout=3) as reply:
            return int(reply.status)
    except HTTPError as exc:
        return exc.code
    except (OSError, URLError, TimeoutError, ValueError):
        return 0


def diagnose() -> tuple[int, int]:
    """Only two non-mutating requests; no shell, arbitrary action or drill header."""
    return _http_probe("/health"), _http_probe("/api/v1/overview", authenticated=True)


def _outcome(status: str, health: int, overview: int) -> tuple[str, bool]:
    if status == "resolved" and health == 200 and overview == 200:
        return "VERIFIED_RESOLVED", True
    if status == "resolved":
        return "RESOLUTION_UNVERIFIED", False
    if health == 200 and overview == 200:
        # A firing alert might have a delayed metric window. This does not
        # prove the underlying failure was only a synthetic drill.
        return "ALERT_ACTIVE_PROBE_HEALTHY", False
    if health == 200 and overview >= 500:
        return "INVESTIGATE_OVERVIEW_FAILURE", False
    return "ABSTAIN_INSUFFICIENT_HEALTH", False


def consume(payload: dict) -> dict:
    status, key, start = _checked_alert(payload)
    with lock:
        with sqlite3.connect(db_path(), timeout=5) as db:
            existing = db.execute(
                "SELECT id,outcome,verified_recovery FROM agent_events "
                "WHERE fingerprint_hash=? AND starts_at=? AND alert_status=?",
                (key, start, status),
            ).fetchone()
            if existing:
                return {"accepted": True, "duplicate": True, "event_id": existing[0],
                        "outcome": existing[1], "action": "NO_ACTION_REPLAY",
                        "verified_recovery": bool(existing[2])}
            health, overview = diagnose()
            result, verified = _outcome(status, health, overview)
            cursor = db.execute(
                "INSERT INTO agent_events "
                "(received_utc,fingerprint_hash,starts_at,alert_status,outcome,action,"
                "health_http,overview_http,verified_recovery) VALUES(?,?,?,?,?,?,?,?,?)",
                (datetime.now(timezone.utc).isoformat(), key, start, status,
                 result, "TWO_READ_ONLY_PROBES", health, overview, int(verified)),
            )
            db.commit()
            return {"accepted": True, "duplicate": False, "event_id": cursor.lastrowid,
                    "outcome": result, "action": "TWO_READ_ONLY_PROBES",
                    "verified_recovery": verified}


def events(limit: int = 20) -> list[dict]:
    limit = max(1, min(limit, 100))
    with sqlite3.connect(db_path(), timeout=5) as db:
        rows = db.execute(
            "SELECT id, received_utc, alert_status, outcome, action, "
            "health_http, overview_http, verified_recovery "
            "FROM agent_events ORDER BY id DESC LIMIT ?", (limit,),
        ).fetchall()
    return [
        dict(zip(("id", "received_utc", "alert_status", "outcome", "action",
                  "health_http", "overview_http", "verified_recovery"), row))
        for row in rows
    ]
