import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_current_org
from app.database import get_db
from app.models.admin_user import AdminUser
from app.models.export import Export
from app.models.organization import Organization
from app.schemas.export import (
    BelcotaxRequest,
    ExportCreatedResponse,
    ExportStatusResponse,
    ExportSummary,
)
from app.services.export_service import process_export

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


def _generate_export_id() -> str:
    return "exp_" + uuid.uuid4().hex[:16]


@router.post(
    "/exports/belcotax",
    response_model=ExportCreatedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit("20/minute")
async def create_export(
    request: Request,
    body: BelcotaxRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
):
    export_id = _generate_export_id()
    export = Export(
        id=export_id,
        org_id=org.id,
        income_year=body.income_year,
        status="pending",
    )
    db.add(export)
    await db.commit()

    background_tasks.add_task(process_export, export_id, body)
    return ExportCreatedResponse(export_id=export_id)


@router.get("/exports/belcotax/{export_id}", response_model=ExportStatusResponse)
async def get_export_status(
    export_id: str,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
):
    export = await db.get(Export, export_id)
    if not export or export.org_id != org.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export niet gevonden")

    summary = None
    if export.summary_json:
        summary = ExportSummary(**export.summary_json)

    return ExportStatusResponse(
        export_id=export.id,
        status=export.status,
        summary=summary,
        error_detail=export.error_detail,
    )


@router.get("/exports/belcotax/{export_id}/xml")
async def download_export_xml(
    export_id: str,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
):
    export = await db.get(Export, export_id)
    if not export or export.org_id != org.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export niet gevonden")
    if export.status != "completed" or not export.xml_content:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Export nog niet voltooid")

    filename = f"belcotax_{export.income_year}_{export_id}.xml"
    return Response(
        content=export.xml_content.encode("utf-8"),
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/exports", response_model=list[ExportStatusResponse])
async def list_all_exports(
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    result = await db.execute(select(Export).order_by(Export.created_at.desc()).limit(200))
    exports = result.scalars().all()
    out = []
    for e in exports:
        summary = ExportSummary(**e.summary_json) if e.summary_json else None
        out.append(ExportStatusResponse(
            export_id=e.id,
            status=e.status,
            summary=summary,
            error_detail=e.error_detail,
        ))
    return out
