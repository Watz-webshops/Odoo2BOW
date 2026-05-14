import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.v1.router import router as v1_router
from app.core.exceptions import AppError, app_error_handler
from app.services.scheduler import shutdown_scheduler, start_scheduler

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    try:
        yield
    finally:
        shutdown_scheduler()


app = FastAPI(
    title="Odoo2BOW Middleware",
    description="Belcotax-on-web 281.86 XML generatie vanuit Odoo data",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

_cors_raw = os.getenv("CORS_ORIGINS", "http://localhost:3000")
_cors_origins = [o.strip() for o in _cors_raw.split(",") if o.strip()]
if _cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


app.add_exception_handler(AppError, app_error_handler)
app.include_router(v1_router, prefix="/api/v1")

# === FRONTEND STATIC FILES SERVING (Next.js export) ===

static_dir = Path(__file__).parent / "static"

# Mount Next's _next subdir (gehashed JS/CSS/chunks). Exact pad uit next-export output.
_next_dir = static_dir / "_next"
if _next_dir.exists():
    app.mount("/_next", StaticFiles(directory=str(_next_dir)), name="next-static")


@app.get("/{full_path:path}", include_in_schema=False)
async def spa(full_path: str):
    """
    Catch-all voor frontend:
    - /api/* en /docs/* worden expliciet uitgesloten (vallen door naar 404).
    - Bestaande bestanden in static/ (bv. /favicon.ico, /robots.txt) worden direct geserveerd.
    - Anders: index.html teruggeven zodat client-side router de route oplost.
    """
    if full_path.startswith("api/") or full_path in ("docs", "redoc", "openapi.json"):
        raise HTTPException(status_code=404)

    if full_path:
        candidate = static_dir / full_path
        # Statische export bouwt routes als `dashboard.html`, `login.html`, ...
        # Probeer eerst exact bestand, daarna met `.html` suffix.
        if candidate.is_file():
            return FileResponse(str(candidate))
        html_candidate = static_dir / f"{full_path}.html"
        if html_candidate.is_file():
            return FileResponse(str(html_candidate))

    index_path = static_dir / "index.html"
    if index_path.is_file():
        return FileResponse(str(index_path), media_type="text/html")
    raise HTTPException(status_code=404, detail="Frontend niet gebouwd")
