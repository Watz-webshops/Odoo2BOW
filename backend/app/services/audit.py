"""Audit logger — schrijft acties naar audit_log tabel."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin_user import AdminUser
from app.models.audit_log import AuditLog
from app.models.user import User

Actor = AdminUser | User | None


async def log_action(
    db: AsyncSession,
    actor: Actor,
    action: str,
    target_type: str | None = None,
    target_id: str | None = None,
    details: dict | None = None,
    ip_address: str | None = None,
) -> None:
    """
    Log een actie. Commit wordt aan de aanroeper overgelaten.
    actor=None voor systeem-acties (bv. cron jobs).
    """
    actor_type = "system"
    actor_id = None
    actor_email = None
    if isinstance(actor, AdminUser):
        actor_type = "admin"
        actor_id = actor.id
        actor_email = actor.email
    elif isinstance(actor, User):
        actor_type = "user"
        actor_id = actor.id
        actor_email = actor.email

    entry = AuditLog(
        actor_type=actor_type,
        actor_id=actor_id,
        actor_email=actor_email,
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=details,
        ip_address=ip_address,
    )
    db.add(entry)
