from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.exports import router as exports_router
from app.api.v1.health import router as health_router
from app.api.v1.organizations import router as organizations_router
from app.api.v1.tokens import router as tokens_router

router = APIRouter()
router.include_router(health_router, tags=["health"])
router.include_router(auth_router, tags=["auth"])
router.include_router(organizations_router, tags=["organizations"])
router.include_router(tokens_router, tags=["tokens"])
router.include_router(exports_router, tags=["exports"])
