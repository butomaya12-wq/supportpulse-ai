"""One-shot bootstrap for a BRAND-NEW isolated synthetic staging PostgreSQL.

No production/local database support. Never place secrets or real customer data here.
Run after Alembic has applied sp_0001_baseline, with a dedicated DB owner.
"""
import json
import os
import re
from datetime import datetime
from pathlib import Path

from psycopg import sql
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app import models as m
from app.auth import DEMO_TENANT
from app.service import evaluate

ROLE = "supportpulse_stage_reader"
TABLES = ("sources", "source_events", "commitments", "findings", "corrective_actions", "audit")
ROOT = Path(__file__).resolve().parents[1]


def validate_target() -> tuple[str, str]:
    if os.getenv("SP_MODE") != "synthetic_staging":
        raise RuntimeError("Bootstrap refused: staging mode required")
    if os.getenv("SP_STAGING_SYNTHETIC_ONLY") != "YES":
        raise RuntimeError("Bootstrap refused: synthetic-only acknowledgment required")
    if os.getenv("SP_STAGE_BOOTSTRAP_CONFIRM") != "BOOTSTRAP_NEW_DISPOSABLE_STAGE_ONLY":
        raise RuntimeError("Bootstrap refused: explicit new staging DB approval required")
    url = os.getenv("DATABASE_URL", "")
    if not url.startswith("postgresql+psycopg://"):
        raise RuntimeError("Bootstrap refused: PostgreSQL psycopg driver required")
    name = make_url(url).database or ""
    if not re.fullmatch(r"[a-zA-Z0-9_]*stage[a-zA-Z0-9_]*", name, flags=re.IGNORECASE):
        raise RuntimeError("Bootstrap refused: staging database naming fence")
    if os.getenv("SP_STAGE_DB_NAME") != name:
        raise RuntimeError("Bootstrap refused: database target mismatch")
    password = os.getenv("SP_STAGE_READ_PASSWORD", "")
    if (len(password) < 48 or not password.isascii() or
            password.startswith(("dev-only", "test-only"))):
        raise RuntimeError("Bootstrap refused: strong staging reader secret required")
    return url, password


def bootstrap() -> None:
    url, password = validate_target()
    engine = create_engine(url, pool_pre_ping=True)
    try:
        with engine.begin() as conn:
            revision = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            if revision != "sp_0001_baseline":
                raise RuntimeError("Bootstrap refused: unexpected Alembic revision")
            if any(conn.execute(select(func.count()).select_from(table)).scalar_one() != 0
                   for table in (m.Source, m.SourceEvent, m.Commitment, m.Finding,
                                 m.CorrectiveAction, m.Audit)):
                raise RuntimeError("Bootstrap refused: tables must be empty; no overwrite")
            with conn.connection.driver_connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (ROLE,))
                if cursor.fetchone():
                    raise RuntimeError("Bootstrap refused: reader role already exists")
                cursor.execute(sql.SQL("CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION PASSWORD {}")
                               .format(sql.Identifier(ROLE), sql.Literal(password)))
                cursor.execute(sql.SQL("ALTER ROLE {} SET default_transaction_read_only = on")
                               .format(sql.Identifier(ROLE)))
                db_name = make_url(url).database
                cursor.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}")
                               .format(sql.Identifier(db_name), sql.Identifier(ROLE)))
                cursor.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(sql.Identifier(ROLE)))
                for table in TABLES:
                    cursor.execute(sql.SQL("GRANT SELECT ON TABLE public.{} TO {}")
                                   .format(sql.Identifier(table), sql.Identifier(ROLE)))

            data = json.loads((ROOT / "fixtures" / "initial.json").read_text(encoding="utf-8"))
            imported = data["import"]
            with Session(bind=conn, expire_on_commit=False) as session:
                source = m.Source(id=imported["source_id"], tenant_id=DEMO_TENANT,
                                  channel=imported["channel"],
                                  watermark=datetime.fromisoformat(imported["watermark"]),
                                  health="HEALTHY" if imported["healthy"] else "DEGRADED")
                session.add(source)
                for event in imported["events"]:
                    session.add(m.SourceEvent(tenant_id=DEMO_TENANT, source_id=source.id,
                                             external_id=event["external_id"],
                                             event_time=datetime.fromisoformat(event["event_time"]),
                                             kind=event["kind"],
                                             conversation_id=event["conversation_id"],
                                             actor_id=event["actor_id"], message=event["message"]))
                session.flush()
                evidence = session.scalar(select(m.SourceEvent).where(
                    m.SourceEvent.source_id == source.id,
                    m.SourceEvent.external_id == data["commitment"]["basis_external_id"]))
                session.add(m.Commitment(
                    tenant_id=DEMO_TENANT, source_id=source.id,
                    conversation_id=evidence.conversation_id, actor_id=evidence.actor_id,
                    action_type="send_quote",
                    due_at=datetime.fromisoformat(data["commitment"]["due_at"]),
                    basis_event_id=evidence.id, state="APPROVED"))
                session.flush()
                results = evaluate(session, DEMO_TENANT, "staging-bootstrap",
                                   datetime.fromisoformat(data["evaluate_as_of"]))
                if len(results) != 1 or results[0]["state"] != "CANDIDATE_OVERDUE":
                    raise RuntimeError("Bootstrap refused: unexpected synthetic evaluation")
        # Check the new role through a separate, genuinely limited login.
        reader_url = make_url(url).set(username=ROLE, password=password)
        read_engine = create_engine(reader_url, pool_pre_ping=True)
        try:
            with read_engine.connect() as conn:
                assert conn.scalar(select(func.count()).select_from(m.Source)) == 1
                assert conn.scalar(select(func.count()).select_from(m.Finding)) == 1
        finally:
            read_engine.dispose()
        print("PASS: one synthetic case, isolated read-only role and expected schema; no real data")
    finally:
        engine.dispose()


if __name__ == "__main__":
    bootstrap()
