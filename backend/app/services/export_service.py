"""
Orchestrates: validate RRNs → aggregate → generate XML → store in DB.
Called as a FastAPI BackgroundTask.
"""
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.export import Export
from app.schemas.export import BelcotaxRequest, ExportSummary, ExportSummaryWarning
from app.services.aggregation import aggregate
from app.services.rrn_validator import validate_rrn
from app.services.xml_generator import generate_bow_xml


async def process_export(export_id: str, request: BelcotaxRequest) -> None:
    async with AsyncSessionLocal() as db:
        export = await db.get(Export, export_id)
        if not export:
            return

        export.status = "processing"
        await db.commit()

        try:
            errors: list[str] = []
            birth_dates: dict[str, str] = {}

            rrns_to_check = set()
            for p in request.participations:
                if p.status == "confirmed":
                    rrns_to_check.add(("parent", p.parent.rrn))
                    rrns_to_check.add(("child", p.child.rrn))

            for role, rrn in rrns_to_check:
                info = validate_rrn(rrn)
                if not info.is_valid:
                    errors.append(f"{role.capitalize()} RRN fout: {info.error}")
                elif info.formatted:
                    birth_dates[rrn] = info.formatted

            if errors:
                export.status = "failed"
                export.error_detail = "\n".join(errors)
                export.summary_json = {"errors": errors, "warnings": []}
                export.completed_at = datetime.now(UTC)
                await db.commit()
                return

            result = aggregate(request, birth_dates)

            if not result.fiches:
                export.status = "failed"
                export.error_detail = "Geen geldige fiches na aggregatie (geen bevestigde deelnames of totaalbedrag = 0)"
                export.completed_at = datetime.now(UTC)
                await db.commit()
                return

            xml_bytes = generate_bow_xml(
                request.income_year,
                request.organization,
                result.fiches,
                export_ref=export_id,
            )

            warnings = [
                ExportSummaryWarning(
                    type=w["type"],
                    parent_rrn=w["parent_rrn"],
                    child_rrn=w["child_rrn"],
                    message=w["message"],
                )
                for w in result.warnings
            ]

            summary = ExportSummary(
                fiche_count=len(result.fiches),
                total_amount_cents=sum(f.total_amount_cents for f in result.fiches),
                total_days=sum(f.total_days for f in result.fiches),
                skipped_count=result.skipped_count,
                warnings=warnings,
                errors=[],
            )

            export.status = "completed"
            export.xml_content = xml_bytes.decode("utf-8")
            export.summary_json = summary.model_dump()
            export.completed_at = datetime.now(UTC)
            await db.commit()

        except Exception as exc:
            export.status = "failed"
            export.error_detail = str(exc)
            export.completed_at = datetime.now(UTC)
            await db.commit()
            raise
