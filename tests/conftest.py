from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app import models  # noqa: F401 - register mappings
from app.db import Base, db_session
from app.main import app


@pytest.fixture()
def ctx():
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


@pytest.fixture()
def supervisor():
    return {"Authorization": "Bearer dev-only-supervisor-token"}


@pytest.fixture()
def manager():
    return {"Authorization": "Bearer dev-only-manager-token"}


@pytest.fixture()
def initial():
    import json
    return json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "initial.json").read_text())
