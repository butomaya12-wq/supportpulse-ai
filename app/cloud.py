"""Read-only, fail-closed synthetic staging API.

Independent of app.main: no local demo bearer tokens, no fixture mutation,
no on-call webhook, no repair drill, no automatic database schema creation.
This is NOT an approved public production deployment.
"""
import hmac
import os
import re
import threading
import time
from collections import deque
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from . import models as m
from .auth import DEMO_TENANT
from .db import db_session
from .service import finding_detail, overview

_SHA = re.compile(r"^[0-9a-f]{40}$")
_REQUESTS_PER_MINUTE = 60
_requests = deque()
_request_lock = threading.Lock()


def validate_staging_environment() -> None:
    if os.getenv("SP_MODE") != "synthetic_staging":
        raise RuntimeError("Cloud API disabled: SP_MODE must be synthetic_staging")
    if os.getenv("SP_STAGING_SYNTHETIC_ONLY") != "YES":
        raise RuntimeError("Cloud API disabled: synthetic-only acknowledgment required")
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url.startswith("postgresql+psycopg://"):
        raise RuntimeError("Cloud API disabled: dedicated PostgreSQL URL required")
    token = os.getenv("SP_STAGE_REVIEWER_TOKEN", "")
    if (len(token) < 48 or not token.isascii() or token.startswith("dev-only")
            or token in {"0" * 48, "1" * 48}):
        raise RuntimeError("Cloud API disabled: strong non-demo reviewer token required")
    hosts = [s.strip().lower() for s in os.getenv("SP_STAGE_ALLOWED_HOSTS", "").split(",") if s.strip()]
    if not hosts or any("*" in h or "/" in h or ":" in h for h in hosts):
        raise RuntimeError("Cloud API disabled: explicit allowed hostnames required")
    sha = os.getenv("RENDER_GIT_COMMIT", "").lower()
    if not _SHA.fullmatch(sha):
        raise RuntimeError("Cloud API disabled: immutable RENDER_GIT_COMMIT required")


@asynccontextmanager
async def lifespan(application: FastAPI):
    validate_staging_environment()
    yield


app = FastAPI(
    title="SupportPulse synthetic staging reader",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


@app.middleware("http")
async def cloud_boundary(request: Request, call_next):
    hostname = (request.headers.get("host") or "").split(":")[0].lower()
    allowed = {h.strip().lower() for h in os.getenv("SP_STAGE_ALLOWED_HOSTS", "").split(",") if h.strip()}
    if hostname not in allowed:
        response = JSONResponse({"detail": "Unrecognized host"}, status_code=400)
    else:
        response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
    response.headers["Strict-Transport-Security"] = "max-age=31536000"
    return response


def reviewer(authorization: str | None = Header(default=None)) -> None:
    expected = os.getenv("SP_STAGE_REVIEWER_TOKEN", "")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Staging reviewer token required", headers={"WWW-Authenticate": "Bearer"})
    supplied = authorization[7:]
    if not expected or not hmac.compare_digest(supplied, expected):
        raise HTTPException(401, "Unauthorized reviewer", headers={"WWW-Authenticate": "Bearer"})
    now = time.monotonic()
    with _request_lock:
        while _requests and now - _requests[0] >= 60:
            _requests.popleft()
        if len(_requests) >= _REQUESTS_PER_MINUTE:
            raise HTTPException(429, "Reviewer request rate exceeded", headers={"Retry-After": "60"})
        _requests.append(now)


@app.get("/health")
def health():
    # Liveness only: no customer data or database status exposed.
    return {"status": "ok", "data_mode": "SYNTHETIC_STAGING", "production_ready": False}


@app.get("/api/v1/reviewer/ready", dependencies=[Depends(reviewer)])
def ready(db: Session = Depends(db_session)):
    # Schema check is read-only; migrations happen outside this app.
    db.execute(text("SELECT 1"))
    db.scalar(select(m.Source.id).limit(1))
    db.scalar(select(m.Finding.id).limit(1))
    return {"status": "ready", "database": "available", "data_mode": "SYNTHETIC_STAGING",
            "release_sha": os.environ["RENDER_GIT_COMMIT"]}


@app.get("/api/v1/reviewer/overview", dependencies=[Depends(reviewer)])
def reviewer_overview(db: Session = Depends(db_session)):
    return {"data": overview(db, DEMO_TENANT), "data_mode": "SYNTHETIC_STAGING",
            "release_sha": os.environ["RENDER_GIT_COMMIT"]}


@app.get("/api/v1/reviewer/findings", dependencies=[Depends(reviewer)])
def reviewer_findings(db: Session = Depends(db_session),
                      limit: int = Query(default=20, ge=1, le=50)):
    cases = db.scalars(select(m.Finding).where(m.Finding.tenant_id == DEMO_TENANT)
                       .order_by(m.Finding.id.desc()).limit(limit)).all()
    return {"data": [finding_detail(db, f) for f in cases], "data_mode": "SYNTHETIC_STAGING",
            "release_sha": os.environ["RENDER_GIT_COMMIT"]}
