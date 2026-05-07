from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class AddressSchema(BaseModel):
    street: str
    zip: str
    city: str
    country_code: int = 150


class ContactSchema(BaseModel):
    name: str
    email: str
    phone: str


class OrganizationPayload(BaseModel):
    organization_id: str | None = None
    kbo: str
    name: str
    address: AddressSchema
    language_code: int = 1
    contact: ContactSchema


class ParentSchema(BaseModel):
    rrn: str
    first_name: str
    last_name: str
    address: AddressSchema


class ChildSchema(BaseModel):
    rrn: str
    first_name: str
    last_name: str
    address: AddressSchema | None = None  # optioneel; fallback naar ouderadres


class ParticipationSchema(BaseModel):
    event_id: str
    event_name: str
    start_date: date
    end_date: date
    days: int = Field(ge=1)
    amount_paid: float = Field(ge=0)
    status: str
    parent: ParentSchema
    child: ChildSchema

    @field_validator("end_date")
    @classmethod
    def end_after_start(cls, v, info):
        if "start_date" in info.data and v < info.data["start_date"]:
            raise ValueError("end_date moet na start_date liggen")
        return v


class BelcotaxRequest(BaseModel):
    income_year: int = Field(ge=2020, le=2099)
    organization: OrganizationPayload
    participations: list[ParticipationSchema] = Field(min_length=1)


class ExportSummaryWarning(BaseModel):
    type: str
    parent_rrn: str
    child_rrn: str
    message: str


class ExportSummary(BaseModel):
    fiche_count: int
    total_amount_cents: int
    total_days: int
    skipped_count: int
    warnings: list[ExportSummaryWarning]
    errors: list[str]


class ExportStatusResponse(BaseModel):
    export_id: str
    status: Literal["pending", "processing", "completed", "failed"]
    summary: ExportSummary | None = None
    error_detail: str | None = None


class ExportCreatedResponse(BaseModel):
    export_id: str
    status: str = "processing"
