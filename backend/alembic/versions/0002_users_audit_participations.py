"""users, audit_log, export_participations

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-07
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_org_id", "users", ["org_id"])

    op.create_table(
        "audit_log",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("actor_type", sa.String(20), nullable=False),
        sa.Column("actor_id", UUID(as_uuid=True), nullable=True),
        sa.Column("actor_email", sa.String(255), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("target_type", sa.String(50), nullable=True),
        sa.Column("target_id", sa.String(100), nullable=True),
        sa.Column("details", JSONB, nullable=True),
        sa.Column("ip_address", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_audit_log_created_at", "audit_log", [sa.text("created_at DESC")])
    op.create_index("ix_audit_log_actor", "audit_log", ["actor_type", "actor_id"])

    op.create_table(
        "export_participations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("export_id", sa.String(20), sa.ForeignKey("exports.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_id", sa.String(100), nullable=True),
        sa.Column("event_name", sa.String(255), nullable=True),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date, nullable=False),
        sa.Column("days", sa.Integer, nullable=False),
        sa.Column("amount_paid_cents", sa.Integer, nullable=False),
        sa.Column("status", sa.String(20), nullable=True),
        sa.Column("parent_rrn", sa.String(11), nullable=False),
        sa.Column("parent_first_name", sa.String(100), nullable=True),
        sa.Column("parent_last_name", sa.String(100), nullable=True),
        sa.Column("child_rrn", sa.String(11), nullable=False),
        sa.Column("child_first_name", sa.String(100), nullable=True),
        sa.Column("child_last_name", sa.String(100), nullable=True),
        sa.Column("child_birth_date", sa.Date, nullable=True),
    )
    op.create_index("ix_export_participations_export_id", "export_participations", ["export_id"])
    op.create_index("ix_export_participations_parent_rrn", "export_participations", ["parent_rrn"])
    op.create_index("ix_export_participations_child_rrn", "export_participations", ["child_rrn"])


def downgrade() -> None:
    op.drop_index("ix_export_participations_child_rrn", table_name="export_participations")
    op.drop_index("ix_export_participations_parent_rrn", table_name="export_participations")
    op.drop_index("ix_export_participations_export_id", table_name="export_participations")
    op.drop_table("export_participations")

    op.drop_index("ix_audit_log_actor", table_name="audit_log")
    op.drop_index("ix_audit_log_created_at", table_name="audit_log")
    op.drop_table("audit_log")

    op.drop_index("ix_users_org_id", table_name="users")
    op.drop_table("users")
