from fastapi import APIRouter

from app.api.v1.admins import router as admins_router
from app.api.v1.audit import router as audit_router
from app.api.v1.auth import router as auth_router
from app.api.v1.exports import router as exports_router
from app.api.v1.health import router as health_router
from app.api.v1.me import router as me_router
from app.api.v1.me_odoo import router as me_odoo_router
from app.api.v1.organizations import router as organizations_router
from app.api.v1.organizations_odoo import router as organizations_odoo_router
from app.api.v1.tokens import router as tokens_router
from app.api.v1.users import router as users_router
from app.api.v1.webhooks import router as webhooks_router

router = APIRouter()
router.include_router(health_router, tags=["health"])
router.include_router(auth_router, tags=["auth"])
router.include_router(organizations_router, tags=["organizations"])
router.include_router(organizations_odoo_router, tags=["organizations-odoo"])
router.include_router(tokens_router, tags=["tokens"])
router.include_router(exports_router, tags=["exports"])
router.include_router(admins_router, tags=["admins"])
router.include_router(users_router, tags=["users"])
router.include_router(audit_router, tags=["audit"])
router.include_router(me_router, tags=["me"])
router.include_router(me_odoo_router, tags=["me-odoo"])
router.include_router(webhooks_router, tags=["webhooks"])
