import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.core.security import generate_password, hash_password
from app.database import get_db
from app.models.admin_user import AdminUser
from app.schemas.user import (
    AdminCreate,
    AdminCreated,
    AdminResponse,
    PasswordResetResponse,
)
from app.services.audit import log_action

router = APIRouter()


@router.get("/admins", response_model=list[AdminResponse])
async def list_admins(
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    result = await db.execute(select(AdminUser).order_by(AdminUser.created_at.desc()))
    return result.scalars().all()


@router.post("/admins", response_model=AdminCreated, status_code=status.HTTP_201_CREATED)
async def create_admin(
    body: AdminCreate,
    db: AsyncSession = Depends(get_db),
    current: AdminUser = Depends(get_current_admin),
):
    existing = await db.execute(select(AdminUser).where(AdminUser.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email bestaat al")

    raw_password = generate_password()
    new_admin = AdminUser(email=body.email, password_hash=hash_password(raw_password))
    db.add(new_admin)
    await db.flush()

    await log_action(
        db, current, "admin.create",
        target_type="admin", target_id=str(new_admin.id),
        details={"email": new_admin.email},
    )
    await db.commit()
    await db.refresh(new_admin)
    return AdminCreated(**AdminResponse.model_validate(new_admin).model_dump(), raw_password=raw_password)


@router.delete("/admins/{admin_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_admin(
    admin_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current: AdminUser = Depends(get_current_admin),
):
    if admin_id == current.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Je kan jezelf niet verwijderen",
        )

    count = await db.scalar(select(func.count()).select_from(AdminUser))
    if count <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kan laatste admin niet verwijderen",
        )

    target = await db.get(AdminUser, admin_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin niet gevonden")

    await log_action(
        db, current, "admin.delete",
        target_type="admin", target_id=str(target.id),
        details={"email": target.email},
    )
    await db.delete(target)
    await db.commit()


@router.post("/admins/{admin_id}/reset-password", response_model=PasswordResetResponse)
async def reset_admin_password(
    admin_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current: AdminUser = Depends(get_current_admin),
):
    target = await db.get(AdminUser, admin_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin niet gevonden")

    raw_password = generate_password()
    target.password_hash = hash_password(raw_password)

    await log_action(
        db, current, "admin.password_reset",
        target_type="admin", target_id=str(target.id),
        details={"email": target.email},
    )
    await db.commit()
    return PasswordResetResponse(raw_password=raw_password)
