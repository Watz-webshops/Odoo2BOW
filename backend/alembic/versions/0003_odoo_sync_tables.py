"""odoo sync tables (connections + events + partners + registrations + sync_log)

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── odoo_connections ────────────────────────────────────────────────────
    op.create_table(
        "odoo_connections",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("url", sa.String(255), nullable=False),
        sa.Column("database", sa.String(100), nullable=False),
        sa.Column("username", sa.String(255), nullable=False),
        sa.Column("api_key_enc", sa.Text, nullable=False),
        sa.Column("webhook_secret", sa.String(64), nullable=False),
        sa.Column("bootstrap_completed", sa.Boolean, server_default=sa.text("FALSE"), nullable=False),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("TRUE"), nullable=False),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    # ── odoo_events ─────────────────────────────────────────────────────────
    op.create_table(
        "odoo_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("odoo_id", sa.Integer, nullable=False),
        sa.Column("name", sa.String(255)),
        sa.Column("date_begin", sa.Date),
        sa.Column("date_end", sa.Date),
        sa.Column("raw", JSONB),
        sa.Column("synced_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.UniqueConstraint("org_id", "odoo_id", name="uq_odoo_events_org_odoo"),
    )
    op.create_index("ix_odoo_events_org_id", "odoo_events", ["org_id"])

    # ── odoo_partners ───────────────────────────────────────────────────────
    op.create_table(
        "odoo_partners",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("odoo_id", sa.Integer, nullable=False),
        sa.Column("name", sa.String(255)),
        sa.Column("email", sa.String(255)),
        sa.Column("phone", sa.String(50)),
        sa.Column("street", sa.String(255)),
        sa.Column("zip", sa.String(10)),
        sa.Column("city", sa.String(100)),
        sa.Column("raw", JSONB),
        sa.Column("synced_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.UniqueConstraint("org_id", "odoo_id", name="uq_odoo_partners_org_odoo"),
    )
    op.create_index("ix_odoo_partners_org_id", "odoo_partners", ["org_id"])

    # ── odoo_registrations ──────────────────────────────────────────────────
    op.create_table(
        "odoo_registrations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("odoo_id", sa.Integer, nullable=False),
        sa.Column("event_odoo_id", sa.Integer, nullable=False),
        sa.Column("partner_odoo_id", sa.Integer, nullable=False),
        sa.Column("state", sa.String(20)),
        sa.Column("ticket_price_cents", sa.Integer),
        sa.Column("child_rrn", sa.String(11)),
        sa.Column("child_first_name", sa.String(100)),
        sa.Column("child_last_name", sa.String(100)),
        sa.Column("parent_rrn", sa.String(11)),
        sa.Column("raw", JSONB),
        sa.Column("synced_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.UniqueConstraint("org_id", "odoo_id", name="uq_odoo_regs_org_odoo"),
    )
    op.create_index("ix_odoo_regs_org_event", "odoo_registrations", ["org_id", "event_odoo_id"])
    op.create_index("ix_odoo_regs_org_child_rrn", "odoo_registrations", ["org_id", "child_rrn"])
    op.create_index("ix_odoo_regs_org_parent_rrn", "odoo_registrations", ["org_id", "parent_rrn"])

    # ── odoo_sync_log ───────────────────────────────────────────────────────
    op.create_table(
        "odoo_sync_log",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sync_type", sa.String(30), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("events_synced", sa.Integer, server_default="0"),
        sa.Column("registrations_synced", sa.Integer, server_default="0"),
        sa.Column("partners_synced", sa.Integer, server_default="0"),
        sa.Column("deleted_count", sa.Integer, server_default="0"),
        sa.Column("error_detail", sa.Text),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_odoo_sync_log_org_started", "odoo_sync_log", ["org_id", sa.text("started_at DESC")])


def downgrade() -> None:
    op.drop_index("ix_odoo_sync_log_org_started", table_name="odoo_sync_log")
    op.drop_table("odoo_sync_log")
    op.drop_index("ix_odoo_regs_org_parent_rrn", table_name="odoo_registrations")
    op.drop_index("ix_odoo_regs_org_child_rrn", table_name="odoo_registrations")
    op.drop_index("ix_odoo_regs_org_event", table_name="odoo_registrations")
    op.drop_table("odoo_registrations")
    op.drop_index("ix_odoo_partners_org_id", table_name="odoo_partners")
    op.drop_table("odoo_partners")
    op.drop_index("ix_odoo_events_org_id", table_name="odoo_events")
    op.drop_table("odoo_events")
    op.drop_table("odoo_connections")
