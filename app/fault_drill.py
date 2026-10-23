"""An isolated, explicitly requested synthetic failure probe — never a real outage.

Only GET /api/v1/overview with a special request header, supervisor auth (enforced
in endpoint), synthetic app mode and a second env flag can return a drill 503.
There is NO mutable global fault switch, timeout, database write or external call.
"""
import os
from fastapi import Request


def synthetic_overview_failure_enabled(request: Request) -> bool:
    return (
        os.environ.get("SP_MODE", "synthetic_local") == "synthetic_local"
        and os.environ.get("SP_FAULT_DRILL_ENABLED") == "1"
        and request.method == "GET"
        and request.headers.get("X-SupportPulse-Drill") == "overview-503"
    )
