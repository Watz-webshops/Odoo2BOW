import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ExportParticipation(Base):
    __tablename__ = "export_participations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    export_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("exports.id", ondelete="CASCADE"), nullable=False
    )
    event_id: Mapped[str | None] = mapped_column(String(100))
    event_name: Mapped[str | None] = mapped_column(String(255))
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    days: Mapped[int] = mapped_column(Integer, nullable=False)
    amount_paid_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str | None] = mapped_column(String(20))
    parent_rrn: Mapped[str] = mapped_column(String(11), nullable=False)
    parent_first_name: Mapped[str | None] = mapped_column(String(100))
    parent_last_name: Mapped[str | None] = mapped_column(String(100))
    child_rrn: Mapped[str] = mapped_column(String(11), nullable=False)
    child_first_name: Mapped[str | None] = mapped_column(String(100))
    child_last_name: Mapped[str | None] = mapped_column(String(100))
    child_birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
