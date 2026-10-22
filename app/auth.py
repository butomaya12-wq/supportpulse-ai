import hmac
import os
from dataclasses import dataclass
from fastapi import Header, HTTPException

DEMO_TENANT = "demo-studio"


@dataclass(frozen=True)
class Principal:
    actor: str
    role: str
    tenant_id: str = DEMO_TENANT


def require_user(authorization: str | None = Header(default=None)) -> Principal:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Bearer token required; synthetic local demo only")
    supplied = authorization[7:]
    creds = (
        (os.environ.get("SP_SUPERVISOR_TOKEN", "dev-only-supervisor-token"), Principal("demo-supervisor", "supervisor")),
        (os.environ.get("SP_MANAGER_TOKEN", "dev-only-manager-token"), Principal("demo-manager-001", "manager")),
    )
    for expected, principal in creds:
        if expected and hmac.compare_digest(supplied, expected):
            return principal
    raise HTTPException(401, "Invalid demo token")


def supervisor_only(principal: Principal):
    if principal.role != "supervisor":
        raise HTTPException(403, "Supervisor role required")
