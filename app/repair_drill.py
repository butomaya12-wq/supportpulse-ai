"""Bounded synthetic dashboard failure latch. Never touches customer or SQL data.

Off unless an explicit, locally configured secret and opt-in flag are present.
In-memory with 10-minute maximum expiry: a crash/restart cannot leave a latched
outage behind. Only an explicit secret-authenticated compare-and-swap repairs it.
"""
import hmac
import os
import threading
import time
from fastapi import HTTPException, Request

_LOCK = threading.RLock()
_EXPIRY = 0.0
_REVISION = 0
_MAX_TTL_SECONDS = 600


def enabled() -> bool:
    return (
        os.environ.get("SP_MODE", "synthetic_local") == "synthetic_local"
        and os.environ.get("SP_REPAIR_DRILL_ENABLED") == "1"
        and len(os.environ.get("SP_REPAIR_TOKEN", "")) >= 32
    )


def require_token(request: Request, intent: str) -> None:
    if not enabled():
        raise HTTPException(404, "Repair drill disabled")
    expected = os.environ["SP_REPAIR_TOKEN"]
    supplied = request.headers.get("authorization", "")
    header = request.headers.get("X-SupportPulse-Repair-Drill", "")
    if (header != intent or not supplied.startswith("Bearer ")
            or not hmac.compare_digest(supplied[7:], expected)):
        raise HTTPException(401, "Synthetic repair authorization required")


def state() -> dict:
    global _EXPIRY
    with _LOCK:
        remaining = max(0, int(_EXPIRY - time.monotonic()))
        if remaining == 0:
            _EXPIRY = 0
        return {
            "state": "BROKEN" if remaining else "READY",
            "revision": _REVISION,
            "ttl_seconds": remaining,
            "data_mode": "SYNTHETIC_ONLY",
        }


def is_broken() -> bool:
    return enabled() and state()["state"] == "BROKEN"


def arm() -> dict:
    global _EXPIRY, _REVISION
    if not enabled():
        raise HTTPException(404, "Repair drill disabled")
    with _LOCK:
        if _EXPIRY > time.monotonic():
            raise HTTPException(409, "Synthetic incident already armed")
        _REVISION += 1
        _EXPIRY = time.monotonic() + _MAX_TTL_SECONDS
        return {"state": "BROKEN", "revision": _REVISION,
                "max_duration_seconds": _MAX_TTL_SECONDS,
                "data_mode": "SYNTHETIC_ONLY"}


def repair(expected_revision: int) -> dict:
    global _EXPIRY
    if not enabled():
        raise HTTPException(404, "Repair drill disabled")
    if not isinstance(expected_revision, int) or isinstance(expected_revision, bool):
        raise HTTPException(422, "Expected revision required")
    with _LOCK:
        if _REVISION != expected_revision or _EXPIRY <= time.monotonic():
            _EXPIRY = 0 if _EXPIRY <= time.monotonic() else _EXPIRY
            raise HTTPException(409, "Incident absent, expired or revision changed")
        _EXPIRY = 0
        return {"state": "READY", "revision": _REVISION,
                "repair_applied": True, "data_mode": "SYNTHETIC_ONLY"}
