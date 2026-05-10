import uuid
from datetime import datetime

from pydantic import BaseModel, HttpUrl


class OdooConnectionUpsert(BaseModel):
    url: str
    database: str
    username: str
    api_key: str  # plaintext bij input; backend versleutelt


class OdooConnectionResponse(BaseModel):
    id: uuid.UUID
    url: str
    database: str
    username: str
    bootstrap_completed: bool
    is_active: bool
    last_sync_at: datetime | None
    webhook_url: str
    webhook_secret_visible: bool = False  # alleen True direct na save/regenerate

    model_config = {"from_attributes": True}


class OdooConnectionWithSecret(OdooConnectionResponse):
    webhook_secret: str  # eenmalig getoond bij create/regenerate


class OdooTestResult(BaseModel):
    connection: str  # 'ok' | 'failed'
    message: str | None = None
    questions_found: list[str] = []
    questions_missing: list[str] = []
    registrations_count: int = 0


class OdooSyncLogEntry(BaseModel):
    id: uuid.UUID
    sync_type: str
    status: str
    events_synced: int
    registrations_synced: int
    partners_synced: int
    deleted_count: int
    error_detail: str | None
    started_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class SyncStatus(BaseModel):
    bootstrap_completed: bool
    last_sync_at: datetime | None
    counts: dict
    recent_syncs: list[OdooSyncLogEntry]


class WebhookPayload(BaseModel):
    model: str  # 'event.event' | 'event.registration' | 'res.partner'
    id: int
    action: str  # 'create' | 'write' | 'unlink'


class ExportFromLocalRequest(BaseModel):
    income_year: int
