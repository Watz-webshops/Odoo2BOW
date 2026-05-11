"""Admin-scoped Odoo endpoints — beheer Odoo connecties per organisatie."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.database import get_db
from app.models.admin_user import AdminUser
from app.models.organization import Organization
from app.schemas.export import ExportCreatedResponse
from app.schemas.export_preview import ExportPreviewResponse
from app.schemas.odoo import (
    ExportFromLocalRequest,
    OdooConnectionResponse,
    OdooConnectionUpsert,
    OdooConnectionWithSecret,
    OdooTestResult,
    SyncStatus,
)
from app.services import odoo_connection_service as svc
from app.services import odoo_data_query as data_q
from app.services.export_preview import preview_export

router = APIRouter()


async def _ensure_org(db: AsyncSession, org_id: uuid.UUID) -> Organization:
    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organisatie niet gevonden")
    return org


@router.get(
    "/organizations/{org_id}/odoo-connection",
    response_model=OdooConnectionResponse | None,
)
async def admin_get_connection(
    org_id: uuid.UUID, request: Request,
    db: AsyncSession = Depends(get_db), _: AdminUser = Depends(get_current_admin),
):
    await _ensure_org(db, org_id)
    return await svc.get_connection(db, org_id, request)


@router.put(
    "/organizations/{org_id}/odoo-connection",
    response_model=OdooConnectionWithSecret,
)
async def admin_upsert_connection(
    org_id: uuid.UUID, body: OdooConnectionUpsert, request: Request,
    db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(get_current_admin),
):
    await _ensure_org(db, org_id)
    return await svc.upsert_connection(db, org_id, body, admin, request)


@router.delete(
    "/organizations/{org_id}/odoo-connection",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def admin_delete_connection(
    org_id: uuid.UUID,
    db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(get_current_admin),
):
    await _ensure_org(db, org_id)
    await svc.delete_connection(db, org_id, admin)


@router.post(
    "/organizations/{org_id}/odoo-connection/test",
    response_model=OdooTestResult,
)
async def admin_test_connection(
    org_id: uuid.UUID,
    db: AsyncSession = Depends(get_db), _: AdminUser = Depends(get_current_admin),
):
    await _ensure_org(db, org_id)
    return await svc.test_connection(db, org_id)


@router.post(
    "/organizations/{org_id}/odoo-connection/bootstrap",
    status_code=status.HTTP_202_ACCEPTED,
)
async def admin_bootstrap(
    org_id: uuid.UUID, background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(get_current_admin),
):
    await _ensure_org(db, org_id)
    return await svc.start_bootstrap(db, org_id, admin, background_tasks)


@router.post(
    "/organizations/{org_id}/odoo-connection/resync",
    status_code=status.HTTP_202_ACCEPTED,
)
async def admin_resync(
    org_id: uuid.UUID, background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(get_current_admin),
):
    await _ensure_org(db, org_id)
    return await svc.start_resync(db, org_id, admin, background_tasks)


@router.get("/organizations/{org_id}/sync-status", response_model=SyncStatus)
async def admin_sync_status(
    org_id: uuid.UUID,
    db: AsyncSession = Depends(get_db), _: AdminUser = Depends(get_current_admin),
):
    await _ensure_org(db, org_id)
    return await svc.get_sync_status(db, org_id)


@router.post(
    "/organizations/{org_id}/exports/from-local",
    response_model=ExportCreatedResponse, status_code=status.HTTP_202_ACCEPTED,
)
async def admin_export_from_local(
    org_id: uuid.UUID, body: ExportFromLocalRequest, background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(get_current_admin),
):
    await _ensure_org(db, org_id)
    return await svc.start_export_from_local(db, org_id, body.income_year, admin, background_tasks)


@router.get(
    "/organizations/{org_id}/exports/preview",
    response_model=ExportPreviewResponse,
)
async def admin_export_preview(
    org_id: uuid.UUID,
    income_year: int,
    test_mode: bool = False,
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    await _ensure_org(db, org_id)
    return await preview_export(db, org_id, income_year, test_mode=test_mode)


# ── Read-only Odoo data per organisatie (admin) ────────────────────────────
@router.get("/organizations/{org_id}/events")
async def admin_events(
    org_id: uuid.UUID,
    db: AsyncSession = Depends(get_db), _: AdminUser = Depends(get_current_admin),
):
    await _ensure_org(db, org_id)
    return await data_q.list_events(db, org_id)


@router.get("/organizations/{org_id}/participations")
async def admin_participations(
    org_id: uuid.UUID,
    income_year: int | None = None,
    parent_rrn: str | None = None,
    child_rrn: str | None = None,
    event_odoo_id: int | None = None,
    db: AsyncSession = Depends(get_db), _: AdminUser = Depends(get_current_admin),
):
    await _ensure_org(db, org_id)
    return await data_q.list_participations(
        db, org_id, income_year, parent_rrn, child_rrn, event_odoo_id,
    )


@router.get("/organizations/{org_id}/beneficiaries")
async def admin_beneficiaries(
    org_id: uuid.UUID,
    db: AsyncSession = Depends(get_db), _: AdminUser = Depends(get_current_admin),
):
    await _ensure_org(db, org_id)
    return await data_q.list_beneficiaries(db, org_id)
