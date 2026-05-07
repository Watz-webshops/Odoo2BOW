from fastapi import APIRouter

from app.services.xsd_validator import get_schema_path

router = APIRouter()


@router.get("/health")
async def health_check():
    xsd_path = get_schema_path()
    return {
        "status": "ok",
        "version": "v1",
        "xsd_validation": "enabled" if xsd_path else "disabled",
        "xsd_path": str(xsd_path) if xsd_path else None,
    }
