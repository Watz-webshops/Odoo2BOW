"""organization multilingual names + certification validity

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-10
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("organizations", sa.Column("name_fr", sa.String(255), nullable=True))
    op.add_column("organizations", sa.Column("street_fr", sa.String(255), nullable=True))
    op.add_column("organizations", sa.Column("city_fr", sa.String(100), nullable=True))
    op.add_column("organizations", sa.Column("name_de", sa.String(255), nullable=True))
    op.add_column("organizations", sa.Column("street_de", sa.String(255), nullable=True))
    op.add_column("organizations", sa.Column("city_de", sa.String(100), nullable=True))
    op.add_column("organizations", sa.Column("cert_validity_start", sa.Date, nullable=True))
    op.add_column("organizations", sa.Column("cert_validity_end", sa.Date, nullable=True))


def downgrade() -> None:
    op.drop_column("organizations", "cert_validity_end")
    op.drop_column("organizations", "cert_validity_start")
    op.drop_column("organizations", "city_de")
    op.drop_column("organizations", "street_de")
    op.drop_column("organizations", "name_de")
    op.drop_column("organizations", "city_fr")
    op.drop_column("organizations", "street_fr")
    op.drop_column("organizations", "name_fr")
