"""
Read-only queries op de gesyncde Odoo mirror data.
Gedeeld tussen /me/* (user) en /organizations/{org_id}/* (admin) endpoints.
"""
from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.odoo_event import OdooEvent
from app.models.odoo_partner import OdooPartner
from app.models.odoo_registration import OdooRegistration


async def list_events(db: AsyncSession, org_id: uuid.UUID) -> list[dict]:
    counts_stmt = (
        select(OdooRegistration.event_odoo_id, func.count().label("n"))
        .where(OdooRegistration.org_id == org_id)
        .group_by(OdooRegistration.event_odoo_id)
    )
    counts_res = await db.execute(counts_stmt)
    counts = {row.event_odoo_id: row.n for row in counts_res.all()}

    stmt = (
        select(OdooEvent).where(OdooEvent.org_id == org_id)
        .order_by(OdooEvent.date_begin.desc())
    )
    result = await db.execute(stmt)
    return [
        {
            "id": str(e.id),
            "odoo_id": e.odoo_id,
            "name": e.name,
            "date_begin": e.date_begin.isoformat() if e.date_begin else None,
            "date_end": e.date_end.isoformat() if e.date_end else None,
            "registration_count": counts.get(e.odoo_id, 0),
            "synced_at": e.synced_at.isoformat() if e.synced_at else None,
        }
        for e in result.scalars().all()
    ]


async def list_participations(
    db: AsyncSession, org_id: uuid.UUID,
    income_year: int | None = None,
    parent_rrn: str | None = None,
    child_rrn: str | None = None,
    event_odoo_id: int | None = None,
) -> list[dict]:
    stmt = (
        select(OdooRegistration, OdooEvent, OdooPartner)
        .join(OdooEvent,
              (OdooEvent.org_id == OdooRegistration.org_id)
              & (OdooEvent.odoo_id == OdooRegistration.event_odoo_id))
        .join(OdooPartner,
              (OdooPartner.org_id == OdooRegistration.org_id)
              & (OdooPartner.odoo_id == OdooRegistration.partner_odoo_id))
        .where(OdooRegistration.org_id == org_id)
        .order_by(OdooEvent.date_begin.desc())
        .limit(500)
    )
    if income_year:
        stmt = stmt.where(
            OdooEvent.date_begin >= date(income_year, 1, 1),
            OdooEvent.date_begin <= date(income_year, 12, 31),
        )
    if parent_rrn:
        stmt = stmt.where(OdooRegistration.parent_rrn == parent_rrn)
    if child_rrn:
        stmt = stmt.where(OdooRegistration.child_rrn == child_rrn)
    if event_odoo_id:
        stmt = stmt.where(OdooRegistration.event_odoo_id == event_odoo_id)

    result = await db.execute(stmt)
    return [
        {
            "id": str(reg.id),
            "odoo_id": reg.odoo_id,
            "event_odoo_id": reg.event_odoo_id,
            "event_name": event.name,
            "start_date": event.date_begin.isoformat() if event.date_begin else None,
            "end_date": event.date_end.isoformat() if event.date_end else None,
            "state": reg.state,
            "amount_paid_cents": reg.ticket_price_cents or 0,
            "parent_rrn": reg.parent_rrn,
            "parent_name": (partner.name or "").strip(),
            "parent_email": partner.email,
            "child_rrn": reg.child_rrn,
            "child_name": f"{reg.child_first_name or ''} {reg.child_last_name or ''}".strip(),
        }
        for reg, event, partner in result.all()
    ]


async def list_beneficiaries(db: AsyncSession, org_id: uuid.UUID) -> list[dict]:
    stmt = (
        select(
            OdooRegistration.parent_rrn,
            OdooRegistration.partner_odoo_id,
            OdooRegistration.child_rrn,
            OdooRegistration.child_first_name,
            OdooRegistration.child_last_name,
        )
        .where(
            OdooRegistration.org_id == org_id,
            OdooRegistration.parent_rrn.is_not(None),
            OdooRegistration.child_rrn.is_not(None),
        )
        .distinct()
    )
    result = await db.execute(stmt)
    rows = result.all()

    partner_ids = {r[1] for r in rows}
    partners_res = await db.execute(
        select(OdooPartner).where(
            OdooPartner.org_id == org_id,
            OdooPartner.odoo_id.in_(partner_ids),
        )
    )
    partners_by_id = {p.odoo_id: p for p in partners_res.scalars().all()}

    return [
        {
            "parent_rrn": r[0],
            "parent_name": (partners_by_id.get(r[1]).name if partners_by_id.get(r[1]) else "") or "",
            "parent_email": partners_by_id.get(r[1]).email if partners_by_id.get(r[1]) else None,
            "child_rrn": r[2],
            "child_name": f"{r[3] or ''} {r[4] or ''}".strip(),
        }
        for r in rows
    ]
