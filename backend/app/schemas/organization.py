import uuid
from datetime import date, datetime

from pydantic import BaseModel, EmailStr


class OrganizationCreate(BaseModel):
    kbo: str
    name: str
    street: str | None = None
    zip: str | None = None
    city: str | None = None
    country_code: int = 150
    language_code: int = 1
    contact_name: str | None = None
    contact_email: EmailStr | None = None
    contact_phone: str | None = None
    name_fr: str | None = None
    street_fr: str | None = None
    city_fr: str | None = None
    name_de: str | None = None
    street_de: str | None = None
    city_de: str | None = None
    cert_validity_start: date | None = None
    cert_validity_end: date | None = None


class OrganizationUpdate(BaseModel):
    name: str | None = None
    street: str | None = None
    zip: str | None = None
    city: str | None = None
    country_code: int | None = None
    language_code: int | None = None
    contact_name: str | None = None
    contact_email: EmailStr | None = None
    contact_phone: str | None = None
    name_fr: str | None = None
    street_fr: str | None = None
    city_fr: str | None = None
    name_de: str | None = None
    street_de: str | None = None
    city_de: str | None = None
    cert_validity_start: date | None = None
    cert_validity_end: date | None = None


class OrganizationResponse(BaseModel):
    id: uuid.UUID
    kbo: str
    name: str
    street: str | None
    zip: str | None
    city: str | None
    country_code: int
    language_code: int
    contact_name: str | None
    contact_email: str | None
    contact_phone: str | None
    name_fr: str | None
    street_fr: str | None
    city_fr: str | None
    name_de: str | None
    street_de: str | None
    city_de: str | None
    cert_validity_start: date | None
    cert_validity_end: date | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiTokenCreate(BaseModel):
    label: str | None = None


class ApiTokenResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    label: str | None
    created_at: datetime
    revoked_at: datetime | None

    model_config = {"from_attributes": True}


class ApiTokenCreated(ApiTokenResponse):
    raw_token: str
