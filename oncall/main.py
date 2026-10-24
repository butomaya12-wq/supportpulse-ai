"""Grafana webhook receiver; guarded local synthetic alerts only."""
import hmac
import json
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from .agent import consume, events, init_store

@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.getenv("SP_MODE") != "synthetic_local":
        raise RuntimeError("Only synthetic local operation is permitted")
    if len(os.getenv("SP_ONCALL_WEBHOOK_TOKEN", "")) < 32:
        raise RuntimeError("A strong on-call webhook secret is required")
    if not os.getenv("SP_SUPERVISOR_TOKEN"):
        raise RuntimeError("Internal supervisor probe token is required")
    init_store()
    yield

app = FastAPI(title="SupportPulse on-call (synthetic only)", lifespan=lifespan,
              docs_url=None, openapi_url=None, redoc_url=None)

def authorize(request: Request):
    secret = os.getenv("SP_ONCALL_WEBHOOK_TOKEN", "")
    provided = request.headers.get("authorization", "")
    if not (len(secret) >= 32 and provided.startswith("Bearer ")
            and hmac.compare_digest(provided[7:], secret)):
        raise HTTPException(401, "Authentication required")

@app.get("/health")
def health():
    return {"status": "ok", "data_mode": "SYNTHETIC_ONLY"}

@app.post("/webhook", status_code=202)
async def webhook(request: Request):
    authorize(request)
    if request.headers.get("content-type", "").split(";")[0].strip().lower() != "application/json":
        raise HTTPException(415, "JSON required")
    raw = await request.body()
    if len(raw) > 16384:
        raise HTTPException(413, "Payload limit exceeded")
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, ValueError):
        raise HTTPException(422, "Invalid JSON") from None
    try:
        return await run_in_threadpool(consume, payload)
    except ValueError:
        raise HTTPException(422, "Unrecognized alert") from None

@app.get("/events")
def history(request: Request, limit: int = Query(default=20, ge=1, le=100)):
    authorize(request)
    return {"events": events(limit), "data_mode": "SYNTHETIC_ONLY"}
