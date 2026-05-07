import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.core.security import generate_password, hash_password
from app.database import get_db
from app.models.admin_user import AdminUser
from app.models.organization import Organization
from app.models.user import User
from app.schemas.user import (
    PasswordResetResponse,
    UserCreate,
    UserCreated,
    UserResponse,
)
from app.services.audit import log_action

router = APIRouter()


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    org_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    stmt = select(User).order_by(User.created_at.desc())
    if org_id:
        stmt = stmt.where(User.org_id == org_id)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/users", response_model=UserCreated, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
    current: AdminUser = Depends(get_current_admin),
):
    org = await db.get(Organization, body.org_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisatie niet gevonden")

    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email bestaat al")

    raw_password = generate_password()
    new_user = User(
        email=body.email,
        org_id=body.org_id,
        password_hash=hash_password(raw_password),
    )
    db.add(new_user)
    await db.flush()

    await log_action(
        db, current, "user.create",
        target_type="user", target_id=str(new_user.id),
        details={"email": new_user.email, "org_id": str(new_user.org_id)},
    )
    await db.commit()
    await db.refresh(new_user)
    return UserCreated(**UserResponse.model_validate(new_user).model_dump(), raw_password=raw_password)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current: AdminUser = Depends(get_current_admin),
):
    target = await db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User niet gevonden")

    await log_action(
        db, current, "user.delete",
        target_type="user", target_id=str(target.id),
        details={"email": target.email, "org_id": str(target.org_id)},
    )
    await db.delete(target)
    await db.commit()


@router.post("/users/{user_id}/reset-password", response_model=PasswordResetResponse)
async def reset_user_password(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current: AdminUser = Depends(get_current_admin),
):
    target = await db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User niet gevonden")

    raw_password = generate_password()
    target.password_hash = hash_password(raw_password)

    await log_action(
        db, current, "user.password_reset",
        target_type="user", target_id=str(target.id),
        details={"email": target.email},
    )
    await db.commit()
    return PasswordResetResponse(raw_password=raw_password)
