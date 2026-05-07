"""User-scoped endpoints — alle data gefilterd op JWT.org_id."""
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import distinct, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.security import generate_api_token, hash_token
from app.database import get_db
from app.models.api_token import ApiToken
from app.models.export import Export
from app.models.export_participation import ExportParticipation
from app.models.organization import Organization
from app.models.user import User
from app.schemas.export import (
    BelcotaxRequest,
    ExportCreatedResponse,
    ExportStatusResponse,
    ExportSummary,
)
from app.schemas.organization import (
    ApiTokenCreate,
    ApiTokenCreated,
    ApiTokenResponse,
    OrganizationResponse,
)
from app.services.audit import log_action
from app.services.export_service import process_export

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


# ── Eigen organisatie ──────────────────────────────────────────────────────
@router.get("/me/organization", response_model=OrganizationResponse)
async def my_organization(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    org = await db.get(Organization, user.org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organisatie niet gevonden")
    return org


# ── Exports (scoped op user.org_id) ────────────────────────────────────────
def _generate_export_id() -> str:
    return "exp_" + uuid.uuid4().hex[:16]


@router.get("/me/exports", response_model=list[ExportStatusResponse])
async def my_exports(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Export).where(Export.org_id == user.org_id).order_by(Export.created_at.desc()).limit(200)
    )
    exports = result.scalars().all()
    return [
        ExportStatusResponse(
            export_id=e.id,
            status=e.status,
            summary=ExportSummary(**e.summary_json) if e.summary_json else None,
            error_detail=e.error_detail,
        )
        for e in exports
    ]


@router.post(
    "/me/exports",
    response_model=ExportCreatedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit("20/minute")
async def create_my_export(
    request: Request,
    body: BelcotaxRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Veiligheidscheck: organisatie in payload moet matchen met user's org
    org = await db.get(Organization, user.org_id)
    if not org or org.kbo != body.organization.kbo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organisatie KBO komt niet overeen met je account",
        )

    export_id = _generate_export_id()
    export = Export(id=export_id, org_id=user.org_id, income_year=body.income_year, status="pending")
    db.add(export)
    await log_action(
        db, user, "export.create",
        target_type="export", target_id=export_id,
        details={"income_year": body.income_year, "n_participations": len(body.participations)},
    )
    await db.commit()

    background_tasks.add_task(process_export, export_id, body)
    return ExportCreatedResponse(export_id=export_id)


@router.get("/me/exports/{export_id}", response_model=ExportStatusResponse)
async def my_export_status(
    export_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    export = await db.get(Export, export_id)
    if not export or export.org_id != user.org_id:
        raise HTTPException(status_code=404, detail="Export niet gevonden")
    return ExportStatusResponse(
        export_id=export.id,
        status=export.status,
        summary=ExportSummary(**export.summary_json) if export.summary_json else None,
        error_detail=export.error_detail,
    )


@router.get("/me/exports/{export_id}/xml")
async def my_export_xml(
    export_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    export = await db.get(Export, export_id)
    if not export or export.org_id != user.org_id:
        raise HTTPException(status_code=404, detail="Export niet gevonden")
    if export.status != "completed" or not export.xml_content:
        raise HTTPException(status_code=409, detail="Export nog niet voltooid")
    filename = f"belcotax_{export.income_year}_{export_id}.xml"
    return Response(
        content=export.xml_content.encode("utf-8"),
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Participations (historiek) ─────────────────────────────────────────────
@router.get("/me/participations")
async def my_participations(
    income_year: int | None = None,
    parent_rrn: str | None = None,
    child_rrn: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = (
        select(ExportParticipation, Export)
        .join(Export, ExportParticipation.export_id == Export.id)
        .where(Export.org_id == user.org_id)
        .order_by(ExportParticipation.start_date.desc())
        .limit(500)
    )
    if income_year:
        stmt = stmt.where(Export.income_year == income_year)
    if parent_rrn:
        stmt = stmt.where(ExportParticipation.parent_rrn == parent_rrn)
    if child_rrn:
        stmt = stmt.where(ExportParticipation.child_rrn == child_rrn)

    result = await db.execute(stmt)
    rows = result.all()
    return [
        {
            "id": str(p.id),
            "export_id": p.export_id,
            "income_year": e.income_year,
            "event_name": p.event_name,
            "start_date": p.start_date.isoformat(),
            "end_date": p.end_date.isoformat(),
            "days": p.days,
            "amount_paid_cents": p.amount_paid_cents,
            "parent_rrn": p.parent_rrn,
            "parent_name": f"{p.parent_first_name or ''} {p.parent_last_name or ''}".strip(),
            "child_rrn": p.child_rrn,
            "child_name": f"{p.child_first_name or ''} {p.child_last_name or ''}".strip(),
            "child_birth_date": p.child_birth_date.isoformat() if p.child_birth_date else None,
        }
        for p, e in rows
    ]


@router.get("/me/beneficiaries")
async def my_beneficiaries(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Geeft unieke ouder/kind paren terug uit alle exports van de eigen org."""
    stmt = (
        select(
            ExportParticipation.parent_rrn,
            ExportParticipation.parent_first_name,
            ExportParticipation.parent_last_name,
            ExportParticipation.child_rrn,
            ExportParticipation.child_first_name,
            ExportParticipation.child_last_name,
            ExportParticipation.child_birth_date,
        )
        .join(Export, ExportParticipation.export_id == Export.id)
        .where(Export.org_id == user.org_id)
        .distinct()
    )
    result = await db.execute(stmt)
    return [
        {
            "parent_rrn": r[0],
            "parent_name": f"{r[1] or ''} {r[2] or ''}".strip(),
            "child_rrn": r[3],
            "child_name": f"{r[4] or ''} {r[5] or ''}".strip(),
            "child_birth_date": r[6].isoformat() if r[6] else None,
        }
        for r in result.all()
    ]


# ── Eigen API tokens ───────────────────────────────────────────────────────
@router.get("/me/api-tokens", response_model=list[ApiTokenResponse])
async def my_tokens(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ApiToken).where(ApiToken.org_id == user.org_id).order_by(ApiToken.created_at.desc())
    )
    return result.scalars().all()


@router.post("/me/api-tokens", response_model=ApiTokenCreated, status_code=status.HTTP_201_CREATED)
async def create_my_token(
    body: ApiTokenCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    raw = generate_api_token()
    token = ApiToken(org_id=user.org_id, token_hash=hash_token(raw), label=body.label)
    db.add(token)
    await db.flush()
    await log_action(
        db, user, "token.create",
        target_type="api_token", target_id=str(token.id),
        details={"org_id": str(user.org_id), "label": body.label},
    )
    await db.commit()
    await db.refresh(token)
    return ApiTokenCreated(**ApiTokenResponse.model_validate(token).model_dump(), raw_token=raw)


@router.delete("/me/api-tokens/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_my_token(
    token_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    token = await db.get(ApiToken, token_id)
    if not token or token.org_id != user.org_id:
        raise HTTPException(status_code=404, detail="Token niet gevonden")
    if token.revoked_at:
        raise HTTPException(status_code=409, detail="Token al ingetrokken")
    token.revoked_at = datetime.now(UTC)
    await log_action(
        db, user, "token.revoke",
        target_type="api_token", target_id=str(token.id),
    )
    await db.commit()
