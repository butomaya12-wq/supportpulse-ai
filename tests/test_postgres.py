"""PostgreSQL-backed API integration checks. Set POSTGRES_TEST_URL only for throwaway CI database."""
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker
from app.db import Base, db_session
from app.main import app
from app import models as m


@pytest.fixture()
def pg_ctx():
    url = os.environ.get('POSTGRES_TEST_URL')
    if not url:
        pytest.skip('POSTGRES_TEST_URL not set: SQLite checks run separately')
    # Dedicated ephemeral CI database only. This fixture drops tables after every test.
    engine = create_engine(url, pool_pre_ping=True)
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
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_postgres_import_is_idempotent(pg_ctx, supervisor, initial):
    c, Session = pg_ctx
    payload = initial['import']
    a = c.post('/api/v1/imports', headers=supervisor, json=payload)
    b = c.post('/api/v1/imports', headers=supervisor, json=payload)
    assert (a.status_code, b.status_code) == (200, 200)
    assert (a.json()['inserted'], b.json()['inserted'], b.json()['deduplicated']) == (2, 0, 2)
    a = c.post('/api/v1/commitments', headers=supervisor, json=initial['commitment'])
    b = c.post('/api/v1/commitments', headers=supervisor, json=initial['commitment'])
    assert a.json()['created'] is True and b.json()['created'] is False
    c.post('/api/v1/evaluate', headers=supervisor, params={'as_of': initial['evaluate_as_of']})
    c.post('/api/v1/evaluate', headers=supervisor, params={'as_of': initial['evaluate_as_of']})
    with Session() as session:
        assert session.scalar(select(func.count()).select_from(m.SourceEvent)) == 2
        assert session.scalar(select(func.count()).select_from(m.Commitment)) == 1
        assert session.scalar(select(func.count()).select_from(m.Finding)) == 1


def test_postgres_unknown_source_never_blames_manager(pg_ctx, supervisor, initial):
    c, _ = pg_ctx
    initial['import']['healthy'] = False
    assert c.post('/api/v1/imports', headers=supervisor, json=initial['import']).status_code == 200
    assert c.post('/api/v1/commitments', headers=supervisor, json=initial['commitment']).status_code == 200
    assert c.post('/api/v1/evaluate', headers=supervisor,
                  params={'as_of': initial['evaluate_as_of']}).status_code == 200
    case = c.get('/api/v1/findings', headers=supervisor).json()['data'][0]
    assert case['state'] == 'INSUFFICIENT_DATA'
    assert case['verification']['ready'] is False
    assert c.post(f'/api/v1/findings/{case["id"]}/review', headers=supervisor,
                  json={'decision': 'CONFIRM', 'reason': 'Do not guess from incomplete source'}).status_code == 409
    assert c.get('/api/v1/overview', headers=supervisor).json()['on_time']['value'] is None
