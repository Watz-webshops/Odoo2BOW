"""
Shared service voor Odoo connectie operaties.
Wordt gebruikt door zowel /me/odoo-connection (user-scoped) als
/organizations/{org_id}/odoo-connection (admin-scoped) endpoints.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

from fastapi import BackgroundTasks, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.crypto import decrypt, encrypt, generate_webhook_secret
from app.models.admin_user import AdminUser
from app.models.export import Export
from app.models.odoo_connection import OdooConnection
from app.models.odoo_event import OdooEvent
from app.models.odoo_partner import OdooPartner
from app.models.odoo_registration import OdooRegistration
from app.models.odoo_sync_log import OdooSyncLog
from app.models.user import User
from app.schemas.export import ExportCreatedResponse
from app.schemas.odoo import (
    OdooConnectionResponse,
    OdooConnectionUpsert,
    OdooConnectionWithSecret,
    OdooSyncLogEntry,
    OdooTestResult,
    SyncStatus,
)
from app.services.audit import log_action
from app.services.export_from_local import process_export_from_local
from app.services.odoo_client import OdooClient
from app.services.odoo_mapper import detect_questions
from app.services.odoo_sync import bootstrap_sync, reconcile

Actor = AdminUser | User


def webhook_url(request: Request, org_id: uuid.UUID) -> str:
    base = str(request.base_url).rstrip("/")
    return f"{base}/api/v1/webhooks/odoo/{org_id}"


def to_response(conn: OdooConnection, request: Request) -> OdooConnectionResponse:
    return OdooConnectionResponse(
        id=conn.id, url=conn.url, database=conn.database, username=conn.username,
        bootstrap_completed=conn.bootstrap_completed,
        is_active=conn.is_active,
        last_sync_at=conn.last_sync_at,
        webhook_url=webhook_url(request, conn.org_id),
    )


# ── CRUD ────────────────────────────────────────────────────────────────────
async def get_connection(
    db: AsyncSession, org_id: uuid.UUID, request: Request,
) -> OdooConnectionResponse | None:
    result = await db.execute(select(OdooConnection).where(OdooConnection.org_id == org_id))
    conn = result.scalar_one_or_none()
    if not conn:
        return None
    return to_response(conn, request)


async def upsert_connection(
    db: AsyncSession, org_id: uuid.UUID, body: OdooConnectionUpsert,
    actor: Actor, request: Request,
) -> OdooConnectionWithSecret:
    if not settings.encryption_key:
        raise HTTPException(status_code=500, detail="ENCRYPTION_KEY not configured")

    result = await db.execute(select(OdooConnection).where(OdooConnection.org_id == org_id))
    conn = result.scalar_one_or_none()

    api_key_enc = encrypt(body.api_key)
    if conn:
        conn.url = body.url
        conn.database = body.database
        conn.username = body.username
        conn.api_key_enc = api_key_enc
        conn.updated_at = datetime.now(UTC)
        action = "odoo.connection.update"
    else:
        conn = OdooConnection(
            org_id=org_id,
            url=body.url, database=body.database, username=body.username,
            api_key_enc=api_key_enc,
            webhook_secret=generate_webhook_secret(),
        )
        db.add(conn)
        action = "odoo.connection.create"

    await db.flush()
    await log_action(
        db, actor, action,
        target_type="odoo_connection", target_id=str(conn.id),
        details={"org_id": str(org_id)},
    )
    await db.commit()
    await db.refresh(conn)

    base = to_response(conn, request)
    return OdooConnectionWithSecret(**base.model_dump(), webhook_secret=conn.webhook_secret)


async def delete_connection(db: AsyncSession, org_id: uuid.UUID, actor: Actor) -> None:
    result = await db.execute(select(OdooConnection).where(OdooConnection.org_id == org_id))
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="No Odoo connection")
    await log_action(
        db, actor, "odoo.connection.delete",
        target_type="odoo_connection", target_id=str(conn.id),
        details={"org_id": str(org_id)},
    )
    await db.delete(conn)
    await db.commit()


# ── Test verbinding ─────────────────────────────────────────────────────────
async def test_connection(db: AsyncSession, org_id: uuid.UUID) -> OdooTestResult:
    result = await db.execute(select(OdooConnection).where(OdooConnection.org_id == org_id))
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="No Odoo connection")

    try:
        client = OdooClient(
            url=conn.url, database=conn.database,
            username=conn.username, api_key=decrypt(conn.api_key_enc),
        )
        await asyncio.to_thread(client.authenticate)

        reg_count = len(await asyncio.to_thread(client.search_ids, "event.registration"))
        all_questions = await asyncio.to_thread(
            client.search_read, "event.question", [], ["title"], 0,
        )
        titles = [q.get("title") or "" for q in all_questions]
        diag = detect_questions(titles)

        return OdooTestResult(
            connection="ok",
            questions_found=diag["found"],
            questions_missing=diag["missing"],
            registrations_count=reg_count,
        )
    except Exception as exc:
        return OdooTestResult(
            connection="failed",
            message=f"{type(exc).__name__}: {exc}",
        )


# ── Bootstrap + resync ──────────────────────────────────────────────────────
async def start_bootstrap(
    db: AsyncSession, org_id: uuid.UUID, actor: Actor, background_tasks: BackgroundTasks,
) -> dict:
    result = await db.execute(select(OdooConnection).where(OdooConnection.org_id == org_id))
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="No Odoo connection")
    background_tasks.add_task(bootstrap_sync, org_id)
    await log_action(
        db, actor, "odoo.bootstrap.start",
        target_id=str(conn.id), details={"org_id": str(org_id)},
    )
    await db.commit()
    return {"status": "started"}


async def start_resync(
    db: AsyncSession, org_id: uuid.UUID, actor: Actor, background_tasks: BackgroundTasks,
) -> dict:
    result = await db.execute(select(OdooConnection).where(OdooConnection.org_id == org_id))
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="No Odoo connection")
    background_tasks.add_task(reconcile, org_id)
    await log_action(
        db, actor, "odoo.resync.start",
        target_id=str(conn.id), details={"org_id": str(org_id)},
    )
    await db.commit()
    return {"status": "started"}


# ── Sync status ─────────────────────────────────────────────────────────────
async def get_sync_status(db: AsyncSession, org_id: uuid.UUID) -> SyncStatus:
    conn_res = await db.execute(select(OdooConnection).where(OdooConnection.org_id == org_id))
    conn = conn_res.scalar_one_or_none()

    counts = {
        "events": await db.scalar(
            select(func.count()).select_from(OdooEvent).where(OdooEvent.org_id == org_id)
        ),
        "partners": await db.scalar(
            select(func.count()).select_from(OdooPartner).where(OdooPartner.org_id == org_id)
        ),
        "registrations": await db.scalar(
            select(func.count()).select_from(OdooRegistration).where(OdooRegistration.org_id == org_id)
        ),
    }

    log_res = await db.execute(
        select(OdooSyncLog)
        .where(OdooSyncLog.org_id == org_id)
        .order_by(OdooSyncLog.started_at.desc())
        .limit(20)
    )

    return SyncStatus(
        bootstrap_completed=conn.bootstrap_completed if conn else False,
        last_sync_at=conn.last_sync_at if conn else None,
        counts=counts,
        recent_syncs=[OdooSyncLogEntry.model_validate(s) for s in log_res.scalars().all()],
    )


# ── Export from local ───────────────────────────────────────────────────────
async def start_export_from_local(
    db: AsyncSession, org_id: uuid.UUID, income_year: int,
    actor: Actor, background_tasks: BackgroundTasks,
) -> ExportCreatedResponse:
    export_id = "exp_" + uuid.uuid4().hex[:16]
    export = Export(id=export_id, org_id=org_id, income_year=income_year, status="pending")
    db.add(export)
    await log_action(
        db, actor, "export.create_from_local",
        target_type="export", target_id=export_id,
        details={"income_year": income_year, "org_id": str(org_id)},
    )
    await db.commit()
    background_tasks.add_task(process_export_from_local, export_id, org_id, income_year)
    return ExportCreatedResponse(export_id=export_id)
