"""
Odoo Online XML-RPC client wrapper.

Doel: alle Odoo-calls op één plek; threadsafe gebruikt vanuit async via asyncio.to_thread.
"""
from __future__ import annotations

import xmlrpc.client
from dataclasses import dataclass


@dataclass
class OdooClient:
    url: str
    database: str
    username: str
    api_key: str
    _uid: int | None = None
    _models: xmlrpc.client.ServerProxy | None = None

    def authenticate(self) -> int:
        """Login. Returnt uid; raise als auth faalt."""
        common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common", allow_none=True)
        uid = common.authenticate(self.database, self.username, self.api_key, {})
        if not uid:
            raise PermissionError("Odoo authentication failed")
        self._uid = uid
        self._models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object", allow_none=True)
        return uid

    def _ensure(self) -> tuple[xmlrpc.client.ServerProxy, int]:
        if self._models is None or self._uid is None:
            self.authenticate()
        return self._models, self._uid  # type: ignore[return-value]

    def execute(self, model: str, method: str, *args, **kwargs):
        models, uid = self._ensure()
        return models.execute_kw(self.database, uid, self.api_key, model, method, list(args), kwargs)

    # ── High-level helpers ────────────────────────────────────────────────────

    def search_read(self, model: str, domain: list, fields: list[str], limit: int = 0, offset: int = 0):
        return self.execute(model, "search_read", domain, fields=fields, limit=limit, offset=offset)

    def get_company(self) -> dict | None:
        rows = self.search_read(
            "res.company",
            [("id", "=", 1)],
            ["name", "vat", "street", "zip", "city", "phone", "email"],
            limit=1,
        )
        return rows[0] if rows else None

    def get_events(self, batch: int = 200) -> list[dict]:
        """Haal alle events binnen (gepagineerd)."""
        all_rows: list[dict] = []
        offset = 0
        while True:
            rows = self.search_read(
                "event.event", [],
                ["id", "name", "date_begin", "date_end"],
                limit=batch, offset=offset,
            )
            if not rows:
                break
            all_rows.extend(rows)
            if len(rows) < batch:
                break
            offset += batch
        return all_rows

    def get_registrations(self, batch: int = 200) -> list[dict]:
        """Haal alle event.registration records (alle states), gepagineerd."""
        all_rows: list[dict] = []
        offset = 0
        fields = [
            "id", "event_id", "partner_id", "state",
            "event_ticket_id", "registration_answer_ids",
        ]
        while True:
            rows = self.search_read("event.registration", [], fields, limit=batch, offset=offset)
            if not rows:
                break
            all_rows.extend(rows)
            if len(rows) < batch:
                break
            offset += batch
        return all_rows

    def get_partners(self, ids: list[int]) -> list[dict]:
        """Haal specifieke partners op."""
        if not ids:
            return []
        return self.search_read(
            "res.partner",
            [("id", "in", ids)],
            ["id", "name", "email", "phone", "street", "zip", "city"],
        )

    def get_event_tickets(self, ids: list[int]) -> dict[int, float]:
        """Returnt mapping ticket_id → price."""
        if not ids:
            return {}
        rows = self.search_read("event.event.ticket", [("id", "in", ids)], ["id", "price"])
        return {r["id"]: float(r.get("price") or 0) for r in rows}

    def get_registration_answers(self, registration_ids: list[int]) -> list[dict]:
        """
        Haal antwoorden van registraties.
        Het Odoo model heet event.registration.answer (met question_id en value).
        """
        if not registration_ids:
            return []
        # In recentere Odoo versies is het 'event.registration.answer'
        rows = self.search_read(
            "event.registration.answer",
            [("registration_id", "in", registration_ids)],
            ["id", "registration_id", "question_id", "value_text_box", "value_answer_id"],
        )
        return rows

    def get_questions(self, ids: list[int]) -> dict[int, str]:
        """Returnt mapping question_id → title."""
        if not ids:
            return {}
        rows = self.search_read("event.question", [("id", "in", ids)], ["id", "title"])
        return {r["id"]: r.get("title") or "" for r in rows}

    def get_question_answer_values(self, ids: list[int]) -> dict[int, str]:
        """Voor multiple-choice antwoorden: mapping answer_id → name."""
        if not ids:
            return {}
        rows = self.search_read("event.question.answer", [("id", "in", ids)], ["id", "name"])
        return {r["id"]: r.get("name") or "" for r in rows}

    # ── ID-only helpers (voor reconciliation) ─────────────────────────────────

    def search_ids(self, model: str, domain: list | None = None) -> list[int]:
        domain = domain or []
        return self.execute(model, "search", domain)
