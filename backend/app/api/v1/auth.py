from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Principal, get_current_principal
from app.core.security import create_access_token, hash_password, verify_password
from app.database import get_db
from app.models.admin_user import AdminUser
from app.models.user import User
from app.schemas.admin import LoginRequest, TokenResponse
from app.schemas.user import ChangePasswordRequest

router = APIRouter()


@router.post("/auth/login")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Probeer eerst admin, dan user. Returnt JWT met juiste role."""
    # Probeer admin
    result = await db.execute(select(AdminUser).where(AdminUser.email == body.email))
    admin = result.scalar_one_or_none()
    if admin and verify_password(body.password, admin.password_hash):
        admin.last_login = datetime.now(UTC)
        await db.commit()
        return {
            "access_token": create_access_token(str(admin.id), role="admin"),
            "token_type": "bearer",
            "role": "admin",
            "user": {"id": str(admin.id), "email": admin.email},
        }

    # Probeer user
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if user and verify_password(body.password, user.password_hash):
        user.last_login = datetime.now(UTC)
        await db.commit()
        return {
            "access_token": create_access_token(
                str(user.id), role="user", org_id=str(user.org_id)
            ),
            "token_type": "bearer",
            "role": "user",
            "user": {"id": str(user.id), "email": user.email, "org_id": str(user.org_id)},
        }

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Ongeldige inloggegevens")


@router.post("/auth/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_own_password(
    body: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    if not verify_password(body.current_password, principal.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Huidig wachtwoord is onjuist"
        )
    if len(body.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Nieuw wachtwoord min. 8 tekens"
        )
    principal.password_hash = hash_password(body.new_password)
    await db.commit()
