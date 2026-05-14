import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
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

# === FRONTEND STATIC FILES SERVING ===

# Create static directories if they don't exist
static_dir = Path(__file__).parent / "static"
assets_dir = static_dir / "assets"
static_dir.mkdir(exist_ok=True)
assets_dir.mkdir(exist_ok=True)

# Mount static assets on /assets (CSS, JS, images, etc.)
if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")


# Root route: serve frontend index.html on /
@app.get("/", include_in_schema=False)
async def serve_frontend_root():
    """Serve frontend login page at root path. Hidden from OpenAPI docs."""
    index_path = static_dir / "index.html"
    if index_path.exists():
        from fastapi.responses import FileResponse
        return FileResponse(str(index_path), media_type="text/html")
    return {"error": "Frontend not found"}, 404


# Catch-all SPA fallback: serve index.html for unknown routes (enables client-side routing)
@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa_fallback(full_path: str):
    """
    Fallback route for SPA client-side routing.
    Catches /login, /dashboard, /reset-password, etc. and returns index.html.
    Excludes /api/* and /docs.
    """
    # Exclude API routes and documentation
    if full_path.startswith("api/") or full_path in ("docs", "openapi.json", "redoc"):
        return {"error": "Not found"}, 404
    
    index_path = static_dir / "index.html"
    if index_path.exists():
        from fastapi.responses import FileResponse
        return FileResponse(str(index_path), media_type="text/html")
    return {"error": "Frontend not found"}, 404
