"""Baseline SupportPulse synthetic evidence schema (staging only).

Revision ID: sp_0001_baseline
Revises:
This migration MUST NOT be applied to an existing owner's local database.
"""
from alembic import op
import sqlalchemy as sa

revision = "sp_0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("tenant_id", sa.String(80), nullable=False),
        sa.Column("channel", sa.String(40), nullable=False),
        sa.Column("watermark", sa.DateTime(timezone=True), nullable=True),
        sa.Column("health", sa.String(24), nullable=False),
    )
    op.create_table(
        "source_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.String(80), nullable=False),
        sa.Column("source_id", sa.String(80), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("external_id", sa.String(100), nullable=False),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("conversation_id", sa.String(100), nullable=False),
        sa.Column("actor_id", sa.String(100), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.UniqueConstraint("tenant_id", "source_id", "external_id", name="unique_provider_event"),
    )
    op.create_table(
        "commitments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.String(80), nullable=False),
        sa.Column("source_id", sa.String(80), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("conversation_id", sa.String(100), nullable=False),
        sa.Column("actor_id", sa.String(100), nullable=False),
        sa.Column("action_type", sa.String(32), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("basis_event_id", sa.Integer(), sa.ForeignKey("source_events.id"), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.UniqueConstraint("tenant_id", "basis_event_id", "action_type", name="unique_approved_promise"),
    )
    op.create_table(
        "findings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.String(80), nullable=False),
        sa.Column("commitment_id", sa.Integer(), sa.ForeignKey("commitments.id"), nullable=False, unique=True),
        sa.Column("state", sa.String(40), nullable=False),
        sa.Column("reviewed_by", sa.String(80), nullable=True),
        sa.Column("review_reason", sa.Text(), nullable=True),
        sa.Column("evidence_event_id", sa.Integer(), sa.ForeignKey("source_events.id"), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False),
    )
    op.create_table(
        "corrective_actions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.String(80), nullable=False),
        sa.Column("finding_id", sa.Integer(), sa.ForeignKey("findings.id"), nullable=False, unique=True),
        sa.Column("owner_id", sa.String(100), nullable=False),
        sa.Column("state", sa.String(40), nullable=False),
        sa.Column("proof_event_id", sa.Integer(), sa.ForeignKey("source_events.id"), nullable=True),
    )
    op.create_table(
        "audit",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.String(80), nullable=False),
        sa.Column("actor", sa.String(100), nullable=False),
        sa.Column("target", sa.String(100), nullable=False),
        sa.Column("action", sa.String(70), nullable=False),
        sa.Column("old_state", sa.String(40), nullable=True),
        sa.Column("new_state", sa.String(40), nullable=True),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
    )
    for table in (
        "sources", "source_events", "commitments", "findings", "corrective_actions", "audit"
    ):
        op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])


def downgrade() -> None:
    # Destructive! Allowed ONLY in throwaway CI databases. NEVER as production rollback.
    for table in (
        "audit", "corrective_actions", "findings", "commitments", "source_events", "sources"
    ):
        op.drop_index(f"ix_{table}_tenant_id", table_name=table)
        op.drop_table(table)
