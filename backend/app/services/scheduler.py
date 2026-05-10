"""
APScheduler voor nightly reconciliation van alle actieve Odoo connections.
Geactiveerd vanuit FastAPI lifespan.
"""
import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.odoo_connection import OdooConnection
from app.services.odoo_sync import reconcile

log = logging.getLogger(__name__)
_scheduler: AsyncIOScheduler | None = None


async def _nightly_reconciliation_job() -> None:
    """Loopt elke nacht — voert reconcile uit voor alle actieve, bootstrapped connections."""
    log.info("Starting nightly reconciliation")
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(OdooConnection).where(
                OdooConnection.is_active.is_(True),
                OdooConnection.bootstrap_completed.is_(True),
            )
        )
        conns = result.scalars().all()

    for conn in conns:
        try:
            log.info("Reconcile org_id=%s", conn.org_id)
            await reconcile(conn.org_id)
        except Exception as exc:
            log.error("Reconcile failed for org_id=%s: %s", conn.org_id, exc)
            # Volgende org niet blokkeren


def start_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = AsyncIOScheduler()
    # Elke nacht om 03:00
    _scheduler.add_job(
        _nightly_reconciliation_job,
        CronTrigger(hour=3, minute=0),
        id="nightly_odoo_reconciliation",
        replace_existing=True,
    )
    _scheduler.start()
    log.info("APScheduler started")


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        log.info("APScheduler stopped")
