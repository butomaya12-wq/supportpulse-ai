"""Staging must never expose local demo operations or credentials."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.cloud import app, _requests
from app.db import Base, db_session
from app import models  # noqa: F401 - register schema


SHA = "a" * 40
REVIEW_TOKEN = "test-only-staging-reviewer-" + "x" * 48


@pytest.fixture
def config(monkeypatch):
    monkeypatch.setenv("SP_MODE", "synthetic_staging")
    monkeypatch.setenv("SP_STAGING_SYNTHETIC_ONLY", "YES")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://staging_reader:placeholder@isolated-db:5432/staging_synthetic")
    monkeypatch.setenv("SP_STAGE_REVIEWER_TOKEN", REVIEW_TOKEN)
    monkeypatch.setenv("SP_STAGE_ALLOWED_HOSTS", "testserver")
    monkeypatch.setenv("RENDER_GIT_COMMIT", SHA)
    _requests.clear()


@pytest.fixture
def stage_client(config):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    def override():
        with Session() as db:
            yield db

    app.dependency_overrides[db_session] = override
    try:
        with TestClient(app) as client:
            yield client, Session
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
        _requests.clear()


def _headers(token=REVIEW_TOKEN):
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize("key,value,expected", [
    ("SP_MODE", "synthetic_local", "SP_MODE"),
    ("SP_MODE", "production", "SP_MODE"),
    ("SP_STAGING_SYNTHETIC_ONLY", "NO", "synthetic-only"),
    ("DATABASE_URL", "sqlite:///public.db", "PostgreSQL"),
    ("SP_STAGE_REVIEWER_TOKEN", "dev-only-supervisor-token", "strong"),
    ("SP_STAGE_REVIEWER_TOKEN", "short", "strong"),
    ("SP_STAGE_ALLOWED_HOSTS", "*", "hostnames"),
    ("RENDER_GIT_COMMIT", "latest", "RENDER_GIT_COMMIT"),
])
def test_fail_closed_before_serving(config, monkeypatch, key, value, expected):
    monkeypatch.setenv(key, value)
    with pytest.raises(RuntimeError, match=expected):
        with TestClient(app):
            pass


def test_read_only_authenticated_staging(stage_client):
    client, _ = stage_client
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["production_ready"] is False
    assert health.headers["Cache-Control"] == "no-store"
    assert health.headers["X-Frame-Options"] == "DENY"
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404
    assert client.get("/api/v1/reviewer/ready").status_code == 401
    assert client.get("/api/v1/reviewer/overview", headers=_headers("wrong")).status_code == 401
    assert client.get("/api/v1/reviewer/ready", headers=_headers()).json()["release_sha"] == SHA
    overview = client.get("/api/v1/reviewer/overview", headers=_headers())
    assert overview.status_code == 200
    assert overview.json()["data"]["impact_rub"] is None
    findings = client.get("/api/v1/reviewer/findings", headers=_headers()).json()
    assert findings["data"] == [] and findings["data_mode"] == "SYNTHETIC_STAGING"


def test_no_mutable_or_local_oncall_routes(stage_client):
    client, _ = stage_client
    for path in ("/api/v1/imports", "/api/v1/commitments", "/api/v1/evaluate",
                 "/api/v1/demo/seed", "/api/v1/demo/followup", "/api/v1/demo/repair-drill/arm",
                 "/webhook"):
        assert client.post(path, headers=_headers(), json={}).status_code == 404, path
    assert client.get("/api/v1/audit", headers=_headers()).status_code == 404
    assert client.get("/api/v1/demo/repair-drill/state", headers=_headers()).status_code == 404


def test_host_fence_and_rate_limit(stage_client):
    client, _ = stage_client
    assert client.get("/health", headers={"Host": "evil.example"}).status_code == 400
    for _ in range(60):
        assert client.get("/api/v1/reviewer/overview", headers=_headers()).status_code == 200
    limited = client.get("/api/v1/reviewer/overview", headers=_headers())
    assert limited.status_code == 429
    assert limited.headers["Retry-After"] == "60"
