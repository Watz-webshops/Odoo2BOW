import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class OdooRegistration(Base):
    __tablename__ = "odoo_registrations"
    __table_args__ = (UniqueConstraint("org_id", "odoo_id", name="uq_odoo_regs_org_odoo"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    odoo_id: Mapped[int] = mapped_column(Integer, nullable=False)
    event_odoo_id: Mapped[int] = mapped_column(Integer, nullable=False)
    partner_odoo_id: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str | None] = mapped_column(String(20))  # 'open' = confirmed
    ticket_price_cents: Mapped[int | None] = mapped_column(Integer)

    # Geparseerde antwoorden (gedenormalized voor snelle queries)
    child_rrn: Mapped[str | None] = mapped_column(String(11))
    child_first_name: Mapped[str | None] = mapped_column(String(100))
    child_last_name: Mapped[str | None] = mapped_column(String(100))
    parent_rrn: Mapped[str | None] = mapped_column(String(11))

    raw: Mapped[dict | None] = mapped_column(JSONB)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
