import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.core.security import generate_api_token, hash_token
from app.database import get_db
from app.models.admin_user import AdminUser
from app.models.api_token import ApiToken
from app.models.organization import Organization
from app.schemas.organization import ApiTokenCreate, ApiTokenCreated, ApiTokenResponse

router = APIRouter()


async def _get_org_or_404(org_id: uuid.UUID, db: AsyncSession) -> Organization:
    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisatie niet gevonden")
    return org


@router.get("/organizations/{org_id}/tokens", response_model=list[ApiTokenResponse])
async def list_tokens(
    org_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    await _get_org_or_404(org_id, db)
    result = await db.execute(
        select(ApiToken).where(ApiToken.org_id == org_id).order_by(ApiToken.created_at.desc())
    )
    return result.scalars().all()


@router.post("/organizations/{org_id}/tokens", response_model=ApiTokenCreated, status_code=status.HTTP_201_CREATED)
async def create_token(
    org_id: uuid.UUID,
    body: ApiTokenCreate,
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    await _get_org_or_404(org_id, db)
    raw = generate_api_token()
    token = ApiToken(org_id=org_id, token_hash=hash_token(raw), label=body.label)
    db.add(token)
    await db.commit()
    await db.refresh(token)
    return ApiTokenCreated(**ApiTokenResponse.model_validate(token).model_dump(), raw_token=raw)


@router.delete("/organizations/{org_id}/tokens/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_token(
    org_id: uuid.UUID,
    token_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    await _get_org_or_404(org_id, db)
    token = await db.get(ApiToken, token_id)
    if not token or token.org_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token niet gevonden")
    if token.revoked_at:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Token is al ingetrokken")

    token.revoked_at = datetime.now(UTC)
    await db.commit()
