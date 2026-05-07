import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    org_id: uuid.UUID


class UserResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    email: EmailStr
    created_at: datetime
    last_login: datetime | None

    model_config = {"from_attributes": True}


class UserCreated(UserResponse):
    raw_password: str  # eenmalig getoond bij aanmaak


class AdminCreate(BaseModel):
    email: EmailStr


class AdminResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    created_at: datetime
    last_login: datetime | None

    model_config = {"from_attributes": True}


class AdminCreated(AdminResponse):
    raw_password: str  # eenmalig getoond


class PasswordResetResponse(BaseModel):
    raw_password: str  # eenmalig getoond


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
