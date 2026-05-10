"""
Sync orchestratie: bootstrap (full XML-RPC fetch), webhook upserts, reconciliation.
Schrijft naar de lokale mirror-tabellen (odoo_events, odoo_partners, odoo_registrations).
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, date, datetime
from typing import Iterable

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt
from app.database import AsyncSessionLocal
from app.models.odoo_connection import OdooConnection
from app.models.odoo_event import OdooEvent
from app.models.odoo_partner import OdooPartner
from app.models.odoo_registration import OdooRegistration
from app.models.odoo_sync_log import OdooSyncLog
from app.services.odoo_client import OdooClient
from app.services.odoo_mapper import parse_answers


async def _client_from_connection(conn: OdooConnection) -> OdooClient:
    return OdooClient(
        url=conn.url,
        database=conn.database,
        username=conn.username,
        api_key=decrypt(conn.api_key_enc),
    )


def _to_date(value) -> date | None:
    if not value:
        return None
    s = str(value)
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        return None


# ── Upsert helpers ──────────────────────────────────────────────────────────
async def _upsert_event(db: AsyncSession, org_id: uuid.UUID, raw: dict) -> None:
    stmt = pg_insert(OdooEvent.__table__).values(
        org_id=org_id,
        odoo_id=raw["id"],
        name=raw.get("name"),
        date_begin=_to_date(raw.get("date_begin")),
        date_end=_to_date(raw.get("date_end")),
        raw=raw,
        synced_at=datetime.now(UTC),
    ).on_conflict_do_update(
        constraint="uq_odoo_events_org_odoo",
        set_={
            "name": raw.get("name"),
            "date_begin": _to_date(raw.get("date_begin")),
            "date_end": _to_date(raw.get("date_end")),
            "raw": raw,
            "synced_at": datetime.now(UTC),
        },
    )
    await db.execute(stmt)


async def _upsert_partner(db: AsyncSession, org_id: uuid.UUID, raw: dict) -> None:
    stmt = pg_insert(OdooPartner.__table__).values(
        org_id=org_id,
        odoo_id=raw["id"],
        name=raw.get("name"),
        email=raw.get("email") or None,
        phone=raw.get("phone") or None,
        street=raw.get("street") or None,
        zip=raw.get("zip") or None,
        city=raw.get("city") or None,
        raw=raw,
        synced_at=datetime.now(UTC),
    ).on_conflict_do_update(
        constraint="uq_odoo_partners_org_odoo",
        set_={
            "name": raw.get("name"),
            "email": raw.get("email") or None,
            "phone": raw.get("phone") or None,
            "street": raw.get("street") or None,
            "zip": raw.get("zip") or None,
            "city": raw.get("city") or None,
            "raw": raw,
            "synced_at": datetime.now(UTC),
        },
    )
    await db.execute(stmt)


async def _upsert_registration(
    db: AsyncSession,
    org_id: uuid.UUID,
    raw: dict,
    ticket_prices: dict[int, float],
    parsed_answers: dict[str, str | None],
) -> None:
    event_id = raw["event_id"][0] if isinstance(raw.get("event_id"), list | tuple) else raw.get("event_id")
    partner_id = raw["partner_id"][0] if isinstance(raw.get("partner_id"), list | tuple) else raw.get("partner_id")
    ticket_id = raw.get("event_ticket_id")
    if isinstance(ticket_id, list | tuple):
        ticket_id = ticket_id[0]
    price_cents = round(ticket_prices.get(ticket_id, 0.0) * 100) if ticket_id else 0

    stmt = pg_insert(OdooRegistration.__table__).values(
        org_id=org_id,
        odoo_id=raw["id"],
        event_odoo_id=event_id,
        partner_odoo_id=partner_id,
        state=raw.get("state"),
        ticket_price_cents=price_cents,
        child_rrn=parsed_answers.get("child_rrn"),
        child_first_name=parsed_answers.get("child_first_name"),
        child_last_name=parsed_answers.get("child_last_name"),
        parent_rrn=parsed_answers.get("parent_rrn"),
        raw=raw,
        synced_at=datetime.now(UTC),
    ).on_conflict_do_update(
        constraint="uq_odoo_regs_org_odoo",
        set_={
            "event_odoo_id": event_id,
            "partner_odoo_id": partner_id,
            "state": raw.get("state"),
            "ticket_price_cents": price_cents,
            "child_rrn": parsed_answers.get("child_rrn"),
            "child_first_name": parsed_answers.get("child_first_name"),
            "child_last_name": parsed_answers.get("child_last_name"),
            "parent_rrn": parsed_answers.get("parent_rrn"),
            "raw": raw,
            "synced_at": datetime.now(UTC),
        },
    )
    await db.execute(stmt)


# ── Sync log helpers ────────────────────────────────────────────────────────
async def _start_sync_log(db: AsyncSession, org_id: uuid.UUID, sync_type: str) -> OdooSyncLog:
    log = OdooSyncLog(org_id=org_id, sync_type=sync_type, status="running")
    db.add(log)
    await db.flush()
    await db.commit()
    return log


async def _finish_sync_log(
    db: AsyncSession, log: OdooSyncLog, *,
    events: int = 0, regs: int = 0, partners: int = 0, deleted: int = 0,
    error: str | None = None,
) -> None:
    """
    Bij error: rollback eerst zodat de aborted transaction wordt opgeruimd,
    dan een fresh write van de log entry.
    """
    if error:
        try:
            await db.rollback()
        except Exception:
            pass
        # Schrijf de error naar een nieuwe log entry of update bestaande via fresh transaction
        log_id = log.id
        log = await db.merge(OdooSyncLog(
            id=log_id,
            org_id=log.org_id,
            sync_type=log.sync_type,
            status="failed",
            error_detail=(error or "")[:2000],  # safety limit
            completed_at=datetime.now(UTC),
            events_synced=events,
            registrations_synced=regs,
            partners_synced=partners,
            deleted_count=deleted,
            started_at=log.started_at,
        ))
    else:
        log.events_synced = events
        log.registrations_synced = regs
        log.partners_synced = partners
        log.deleted_count = deleted
        log.status = "completed"
        log.completed_at = datetime.now(UTC)
    await db.commit()


# ── Bootstrap (full sync) ───────────────────────────────────────────────────
async def bootstrap_sync(org_id: uuid.UUID) -> None:
    """
    Volledige Odoo→lokaal sync. Async wrapper rond sync XML-RPC calls.
    Loopt in BackgroundTask.
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(OdooConnection).where(OdooConnection.org_id == org_id)
        )
        conn = result.scalar_one_or_none()
        if not conn:
            return

        log = await _start_sync_log(db, org_id, sync_type="bootstrap")
        try:
            client = await _client_from_connection(conn)
            # Auth gebeurt sync; uitvoeren in thread om event loop niet te blokkeren
            await asyncio.to_thread(client.authenticate)

            # 1. Events
            events = await asyncio.to_thread(client.get_events)
            for ev in events:
                await _upsert_event(db, org_id, ev)

            # 2. Registrations + dependencies
            regs = await asyncio.to_thread(client.get_registrations)

            # Verzamel ticket_ids + question_ids + partner_ids
            ticket_ids: set[int] = set()
            partner_ids: set[int] = set()
            for r in regs:
                tid = r.get("event_ticket_id")
                if isinstance(tid, list | tuple):
                    tid = tid[0]
                if tid:
                    ticket_ids.add(tid)
                pid = r.get("partner_id")
                if isinstance(pid, list | tuple):
                    pid = pid[0]
                if pid:
                    partner_ids.add(pid)

            ticket_prices = await asyncio.to_thread(client.get_event_tickets, list(ticket_ids))
            partners = await asyncio.to_thread(client.get_partners, list(partner_ids))
            for p in partners:
                await _upsert_partner(db, org_id, p)

            # Antwoorden batch ophalen
            reg_ids = [r["id"] for r in regs]
            answers = await asyncio.to_thread(client.get_registration_answers, reg_ids)

            # Vragen + multi-choice antwoorden
            question_ids: set[int] = set()
            answer_value_ids: set[int] = set()
            for a in answers:
                q = a.get("question_id")
                if isinstance(q, list | tuple):
                    q = q[0]
                if q:
                    question_ids.add(q)
                v = a.get("value_answer_id")
                if isinstance(v, list | tuple):
                    v = v[0]
                if v:
                    answer_value_ids.add(v)

            question_titles = await asyncio.to_thread(client.get_questions, list(question_ids))
            answer_values = await asyncio.to_thread(client.get_question_answer_values, list(answer_value_ids))

            # Group answers per registration
            answers_per_reg: dict[int, list[dict]] = {}
            for a in answers:
                rid = a.get("registration_id")
                if isinstance(rid, list | tuple):
                    rid = rid[0]
                answers_per_reg.setdefault(rid, []).append(a)

            for r in regs:
                parsed = parse_answers(
                    answers_per_reg.get(r["id"], []),
                    question_titles, answer_values,
                )
                await _upsert_registration(db, org_id, r, ticket_prices, parsed)

            # Mark connection
            conn.bootstrap_completed = True
            conn.last_sync_at = datetime.now(UTC)
            await _finish_sync_log(
                db, log,
                events=len(events), regs=len(regs), partners=len(partners),
            )
        except Exception as exc:
            await _finish_sync_log(db, log, error=f"{type(exc).__name__}: {exc}")
            raise


# ── Webhook handler — single record sync ────────────────────────────────────
async def sync_one(org_id: uuid.UUID, model: str, odoo_id: int, action: str) -> None:
    """Verwerk een webhook: fetch het record uit Odoo en upsert/delete lokaal."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(OdooConnection).where(OdooConnection.org_id == org_id))
        conn = result.scalar_one_or_none()
        if not conn:
            return

        log = await _start_sync_log(db, org_id, sync_type="webhook")
        try:
            if action == "unlink":
                if model == "event.event":
                    await db.execute(delete(OdooEvent).where(
                        OdooEvent.org_id == org_id, OdooEvent.odoo_id == odoo_id))
                elif model == "event.registration":
                    await db.execute(delete(OdooRegistration).where(
                        OdooRegistration.org_id == org_id, OdooRegistration.odoo_id == odoo_id))
                elif model == "res.partner":
                    await db.execute(delete(OdooPartner).where(
                        OdooPartner.org_id == org_id, OdooPartner.odoo_id == odoo_id))
                await _finish_sync_log(db, log, deleted=1)
                return

            client = await _client_from_connection(conn)
            await asyncio.to_thread(client.authenticate)

            counts = {"events": 0, "regs": 0, "partners": 0}

            if model == "event.event":
                rows = await asyncio.to_thread(
                    client.search_read, "event.event", [("id", "=", odoo_id)],
                    ["id", "name", "date_begin", "date_end"], 1,
                )
                if rows:
                    await _upsert_event(db, org_id, rows[0])
                    counts["events"] = 1

            elif model == "res.partner":
                rows = await asyncio.to_thread(client.get_partners, [odoo_id])
                if rows:
                    await _upsert_partner(db, org_id, rows[0])
                    counts["partners"] = 1

            elif model == "event.registration":
                rows = await asyncio.to_thread(
                    client.search_read, "event.registration", [("id", "=", odoo_id)],
                    ["id", "event_id", "partner_id", "state", "event_ticket_id", "registration_answer_ids"], 1,
                )
                if rows:
                    r = rows[0]
                    # Trek tickets, partners, antwoorden
                    tid = r.get("event_ticket_id")
                    if isinstance(tid, list | tuple):
                        tid = tid[0]
                    ticket_prices = await asyncio.to_thread(client.get_event_tickets, [tid] if tid else [])

                    pid = r.get("partner_id")
                    if isinstance(pid, list | tuple):
                        pid = pid[0]
                    if pid:
                        partners = await asyncio.to_thread(client.get_partners, [pid])
                        for p in partners:
                            await _upsert_partner(db, org_id, p)
                            counts["partners"] += 1

                    answers = await asyncio.to_thread(client.get_registration_answers, [r["id"]])
                    qids = {(a["question_id"][0] if isinstance(a.get("question_id"), list | tuple) else a.get("question_id"))
                            for a in answers if a.get("question_id")}
                    avids = {(a["value_answer_id"][0] if isinstance(a.get("value_answer_id"), list | tuple) else a.get("value_answer_id"))
                             for a in answers if a.get("value_answer_id")}
                    qtitles = await asyncio.to_thread(client.get_questions, list(qids))
                    avalues = await asyncio.to_thread(client.get_question_answer_values, list(avids))

                    parsed = parse_answers(answers, qtitles, avalues)
                    await _upsert_registration(db, org_id, r, ticket_prices, parsed)
                    counts["regs"] = 1

            conn.last_sync_at = datetime.now(UTC)
            await _finish_sync_log(db, log,
                events=counts["events"], regs=counts["regs"], partners=counts["partners"],
            )
        except Exception as exc:
            await _finish_sync_log(db, log, error=f"{type(exc).__name__}: {exc}")
            raise


# ── Reconciliation (nightly) ────────────────────────────────────────────────
async def reconcile(org_id: uuid.UUID) -> None:
    """
    Vergelijk Odoo IDs met lokaal:
      - Records die lokaal staan maar niet in Odoo → DELETE
      - Records die in Odoo zijn maar lokaal niet → UPSERT (via bootstrap path)
    Voor V1: simpele aanpak — herhaal bootstrap + delete-niet-in-odoo.
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(OdooConnection).where(OdooConnection.org_id == org_id))
        conn = result.scalar_one_or_none()
        if not conn or not conn.is_active:
            return

        log = await _start_sync_log(db, org_id, sync_type="reconciliation")
        try:
            client = await _client_from_connection(conn)
            await asyncio.to_thread(client.authenticate)

            # Haal alle Odoo IDs op
            event_ids = set(await asyncio.to_thread(client.search_ids, "event.event"))
            reg_ids = set(await asyncio.to_thread(client.search_ids, "event.registration"))

            # Lokale IDs
            local_events = await db.execute(
                select(OdooEvent.odoo_id).where(OdooEvent.org_id == org_id)
            )
            local_event_ids = {row[0] for row in local_events.all()}

            local_regs = await db.execute(
                select(OdooRegistration.odoo_id).where(OdooRegistration.org_id == org_id)
            )
            local_reg_ids = {row[0] for row in local_regs.all()}

            # Verwijder lokale die niet in Odoo zijn
            deleted = 0
            stale_events = local_event_ids - event_ids
            if stale_events:
                await db.execute(delete(OdooEvent).where(
                    OdooEvent.org_id == org_id, OdooEvent.odoo_id.in_(stale_events)))
                deleted += len(stale_events)

            stale_regs = local_reg_ids - reg_ids
            if stale_regs:
                await db.execute(delete(OdooRegistration).where(
                    OdooRegistration.org_id == org_id, OdooRegistration.odoo_id.in_(stale_regs)))
                deleted += len(stale_regs)

            await _finish_sync_log(db, log, deleted=deleted)

            # Nu een bootstrap-sync om missende records bij te werken (en update bestaande)
            await bootstrap_sync(org_id)

        except Exception as exc:
            await _finish_sync_log(db, log, error=f"{type(exc).__name__}: {exc}")
            raise
