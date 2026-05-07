"""
Toekomstige automatische indiening via Belcotax bulks API.

Officiële endpoint (nog niet publiek beschikbaar — wijzigt vóór productie):
  https://server.minfin.be/external/api/bulks/v1

Deze module bevat enkel een interface-skeleton. De daadwerkelijke implementatie
volgt zodra de FOD Financiën de productie-URL en authenticatie publiceert.

Tot die tijd blijft de flow:
  1. Middleware genereert XML  →  2. organisatie downloadt XML  →
  3. organisatie uploadt manueel in Belcotax-on-web web-UI.
"""
from dataclasses import dataclass


@dataclass
class BulkSubmissionResult:
    success: bool
    submission_id: str | None
    message: str


async def submit_to_belcotax(xml_bytes: bytes, kbo: str) -> BulkSubmissionResult:
    """
    Placeholder voor toekomstige automatische indiening.
    Geeft voorlopig altijd 'not implemented' terug.
    """
    _ = (xml_bytes, kbo)
    return BulkSubmissionResult(
        success=False,
        submission_id=None,
        message="Bulk API nog niet beschikbaar; gebruik manuele upload in BOW.",
    )
