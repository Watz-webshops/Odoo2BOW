import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kbo: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    street: Mapped[str | None] = mapped_column(String(255))
    zip: Mapped[str | None] = mapped_column(String(10))
    city: Mapped[str | None] = mapped_column(String(100))
    country_code: Mapped[int] = mapped_column(Integer, default=150)
    language_code: Mapped[int] = mapped_column(Integer, default=1)
    contact_name: Mapped[str | None] = mapped_column(String(255))
    contact_email: Mapped[str | None] = mapped_column(String(255))
    contact_phone: Mapped[str | None] = mapped_column(String(50))
    # Anderstalige benamingen voor BOW aangifte (optioneel)
    name_fr: Mapped[str | None] = mapped_column(String(255))
    street_fr: Mapped[str | None] = mapped_column(String(255))
    city_fr: Mapped[str | None] = mapped_column(String(100))
    name_de: Mapped[str | None] = mapped_column(String(255))
    street_de: Mapped[str | None] = mapped_column(String(255))
    city_de: Mapped[str | None] = mapped_column(String(100))
    # Certificeringsgeldigheid — wanneer ingevuld worden f86_2164/2171 op alle fiches geschreven
    cert_validity_start: Mapped[date | None] = mapped_column(Date)
    cert_validity_end: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    tokens: Mapped[list["ApiToken"]] = relationship("ApiToken", back_populates="organization", lazy="select")
    exports: Mapped[list["Export"]] = relationship("Export", back_populates="organization", lazy="select")
