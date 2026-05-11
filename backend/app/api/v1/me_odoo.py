"""User-scoped Odoo endpoints (delegate naar shared service)."""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
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
from app.services.export_preview import preview_export

router = APIRouter()


@router.get("/me/odoo-connection", response_model=OdooConnectionResponse | None)
async def get_my_connection(
    request: Request, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    return await svc.get_connection(db, user.org_id, request)


@router.put("/me/odoo-connection", response_model=OdooConnectionWithSecret)
async def upsert_my_connection(
    body: OdooConnectionUpsert, request: Request,
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    return await svc.upsert_connection(db, user.org_id, body, user, request)


@router.delete("/me/odoo-connection", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_connection(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    await svc.delete_connection(db, user.org_id, user)


@router.post("/me/odoo-connection/test", response_model=OdooTestResult)
async def test_my_connection(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    return await svc.test_connection(db, user.org_id)


@router.post("/me/odoo-connection/bootstrap", status_code=status.HTTP_202_ACCEPTED)
async def bootstrap_my_connection(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    return await svc.start_bootstrap(db, user.org_id, user, background_tasks)


@router.post("/me/odoo-connection/resync", status_code=status.HTTP_202_ACCEPTED)
async def resync_my_connection(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    return await svc.start_resync(db, user.org_id, user, background_tasks)


@router.get("/me/sync-status", response_model=SyncStatus)
async def my_sync_status(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    return await svc.get_sync_status(db, user.org_id)


@router.post(
    "/me/exports/from-local",
    response_model=ExportCreatedResponse, status_code=status.HTTP_202_ACCEPTED,
)
async def create_export_from_local(
    body: ExportFromLocalRequest, background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    return await svc.start_export_from_local(db, user.org_id, body.income_year, user, background_tasks)


@router.get("/me/exports/preview", response_model=ExportPreviewResponse)
async def my_export_preview(
    income_year: int,
    test_mode: bool = False,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await preview_export(db, user.org_id, income_year, test_mode=test_mode)
