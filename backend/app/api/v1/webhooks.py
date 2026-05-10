"""
Webhook endpoint voor Odoo automation rules.
Authenticatie via HMAC SHA-256 met per-org secret.
"""
import hashlib
import hmac
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.odoo_connection import OdooConnection
from app.schemas.odoo import WebhookPayload
from app.services.odoo_sync import sync_one

router = APIRouter()

ALLOWED_MODELS = {"event.event", "event.registration", "res.partner"}
ALLOWED_ACTIONS = {"create", "write", "unlink"}


def _verify_signature(secret: str, body: bytes, signature_header: str | None) -> bool:
    if not signature_header:
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if signature_header.startswith("sha256="):
        signature_header = signature_header[7:]
    return hmac.compare_digest(expected, signature_header)


@router.post("/webhooks/odoo/{org_id}", status_code=status.HTTP_202_ACCEPTED)
async def odoo_webhook(
    org_id: uuid.UUID,
    request: Request,
    background_tasks: BackgroundTasks,
    x_odoo2bow_signature: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    body = await request.body()

    # Connection ophalen
    result = await db.execute(select(OdooConnection).where(OdooConnection.org_id == org_id))
    conn = result.scalar_one_or_none()
    if not conn or not conn.is_active:
        raise HTTPException(status_code=404, detail="No active Odoo connection for this org")

    # HMAC verifiëren
    if not _verify_signature(conn.webhook_secret, body, x_odoo2bow_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Payload parsen
    try:
        payload = WebhookPayload.model_validate_json(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid payload")

    if payload.model not in ALLOWED_MODELS:
        raise HTTPException(status_code=400, detail=f"Model not supported: {payload.model}")
    if payload.action not in ALLOWED_ACTIONS:
        raise HTTPException(status_code=400, detail=f"Action not supported: {payload.action}")

    # Async sync triggeren
    background_tasks.add_task(sync_one, org_id, payload.model, payload.id, payload.action)
    return {"status": "accepted"}
