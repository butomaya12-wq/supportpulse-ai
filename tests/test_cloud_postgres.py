"""Read-only staging route verified against actual ephemeral CI PostgreSQL."""
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.cloud import app
from app.db import Base, db_session
from app import models as m


def test_staging_reads_isolated_postgres_without_mutations(monkeypatch):
    test_url = os.getenv("POSTGRES_TEST_URL")
    if not test_url:
        pytest.skip("Dedicated throwaway Postgres is not configured")
    engine = create_engine(test_url, pool_pre_ping=True)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    with Session.begin() as session:
        session.add(m.Source(id="staging-synthetic-001", tenant_id="demo-studio",
                             channel="synthetic-only", health="HEALTHY"))
        session.add(m.Source(id="hidden-other-tenant", tenant_id="private-tenant",
                             channel="synthetic-only", health="HEALTHY"))

    def override():
        with Session() as session:
            yield session

    token = "isolated-ci-reviewer-" + "q" * 64
    monkeypatch.setenv("SP_MODE", "synthetic_staging")
    monkeypatch.setenv("SP_STAGING_SYNTHETIC_ONLY", "YES")
    monkeypatch.setenv("DATABASE_URL", test_url)
    monkeypatch.setenv("SP_STAGE_ALLOWED_HOSTS", "testserver")
    monkeypatch.setenv("SP_STAGE_REVIEWER_TOKEN", token)
    monkeypatch.setenv("RENDER_GIT_COMMIT", "b" * 40)
    app.dependency_overrides[db_session] = override
    try:
        with TestClient(app) as client:
            auth = {"Authorization": "Bearer " + token}
            assert client.get("/api/v1/reviewer/ready", headers=auth).status_code == 200
            overview = client.get("/api/v1/reviewer/overview", headers=auth)
            assert overview.status_code == 200, overview.text
            assert overview.json()["data_mode"] == "SYNTHETIC_STAGING"
            assert client.get("/api/v1/reviewer/findings", headers=auth).json()["data"] == []
            assert client.post("/api/v1/imports", headers=auth, json={}).status_code == 404
        with Session() as session:
            assert session.scalar(select(func.count()).select_from(m.Source)) == 2
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
