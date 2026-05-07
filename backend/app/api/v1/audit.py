from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.database import get_db
from app.models.admin_user import AdminUser
from app.models.audit_log import AuditLog
from app.schemas.audit import AuditLogEntry

router = APIRouter()


@router.get("/audit-log", response_model=list[AuditLogEntry])
async def list_audit_log(
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    actor_type: str | None = Query(default=None),
    action: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
    if actor_type:
        stmt = stmt.where(AuditLog.actor_type == actor_type)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    result = await db.execute(stmt)
    return result.scalars().all()
