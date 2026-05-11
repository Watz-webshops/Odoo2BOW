"""odoo_events: date_begin/date_end Date -> DateTime (for half-day BOW classification)

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-10
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # USING-cast: bestaande Date-waarden converteren naar timestamp om 00:00:00 lokaal.
    op.alter_column(
        "odoo_events", "date_begin",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.Date(),
        existing_nullable=True,
        postgresql_using="date_begin::timestamp with time zone",
    )
    op.alter_column(
        "odoo_events", "date_end",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.Date(),
        existing_nullable=True,
        postgresql_using="date_end::timestamp with time zone",
    )


def downgrade() -> None:
    op.alter_column(
        "odoo_events", "date_end",
        type_=sa.Date(),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=True,
        postgresql_using="date_end::date",
    )
    op.alter_column(
        "odoo_events", "date_begin",
        type_=sa.Date(),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=True,
        postgresql_using="date_begin::date",
    )
