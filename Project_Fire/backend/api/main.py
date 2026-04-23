"""
main.py – FastAPI application entry point for the Wildfire Detection API.

Start the server with:
    uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
"""

import logging
import os
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from api.config.settings import settings
from api.routes import auth, detections, inference, notifications

# ──────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s – %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Application factory
# ──────────────────────────────────────────────
app = FastAPI(
    title="Wildfire Detection API",
    description=(
        "Real-time wildfire detection and notification system. "
        "Accepts image-based reports from the mobile app, reverse-geocodes "
        "locations, stores detections in Firestore, and dispatches alerts to "
        "nearby fire stations."
    ),
    version="2.0.0",
    # Disable the auto-generated docs URLs; we expose custom ones below.
    docs_url=None,
    redoc_url=None,
    openapi_url="/api/openapi.json",
    contact={"name": "Fire GITHUB Team"},
    license_info={"name": "MIT"},
)

# ──────────────────────────────────────────────
# Static files (offline Swagger / ReDoc assets)
# ──────────────────────────────────────────────
_static_path = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_static_path):
    app.mount("/api/static", StaticFiles(directory=_static_path), name="static")
    logger.info("Static files mounted from %s", _static_path)
else:
    logger.warning("Static directory not found at %s – API docs assets may be missing.", _static_path)


# ──────────────────────────────────────────────
# Custom API docs routes
# ──────────────────────────────────────────────
@app.get("/api/docs", include_in_schema=False, tags=["Documentation"])
async def custom_swagger_ui():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} – Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="/api/static/swagger-ui-bundle.js",
        swagger_css_url="/api/static/swagger-ui.css",
    )


@app.get("/api/redoc", include_in_schema=False, tags=["Documentation"])
async def custom_redoc():
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} – ReDoc",
        redoc_js_url="/api/static/redoc.standalone.js",
    )


# ──────────────────────────────────────────────
# CORS
# ──────────────────────────────────────────────
_allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",  # Vite dev server
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────
# Routers
# ──────────────────────────────────────────────
app.include_router(auth.router,          prefix="/api/auth",          tags=["Authentication"])
app.include_router(detections.router,    prefix="/api/detections",    tags=["Detections"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])
app.include_router(inference.router,     prefix="/api/inference",     tags=["Inference"])


# ──────────────────────────────────────────────
# Core routes
# ──────────────────────────────────────────────
@app.get("/", tags=["Meta"])
async def root():
    """API root – confirms the service is running."""
    return {
        "message": "🔥 Wildfire Detection System API",
        "version": app.version,
        "status": "operational",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "docs": "/api/docs",
    }


@app.get("/api/health", tags=["Meta"])
async def health_check():
    """Lightweight health-check endpoint for load-balancers and uptime monitors."""
    from api.services.redis_service import cache

    try:
        redis_status = "connected" if cache.redis and cache.redis.ping() else "offline"
    except Exception:
        redis_status = "offline"
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "services": {
            "database": "connected",
            "storage": "connected",
            "cache": redis_status,
        },
    }


@app.get("/api/stats", tags=["Meta"])
async def get_stats():
    """Dashboard statistics: total, active, resolved, and by-severity counts."""
    try:
        from api.services.stats_service import stats_service

        stats = await stats_service.get_dashboard_stats()
        return stats
    except Exception as exc:
        logger.error("Stats service error: %s", exc, exc_info=True)
        return {
            "total_detections": 0,
            "active_fires": 0,
            "resolved_fires": 0,
            "critical_fires": 0,
            "today_detections": 0,
            "by_severity": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "by_status": {
                "pending": 0,
                "verified": 0,
                "contained": 0,
                "false_alarm": 0,
                "resolved": 0,
            },
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "error": str(exc),
        }


# ──────────────────────────────────────────────
# Global exception handler
# ──────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all handler – logs the full traceback and returns a safe 500 response."""
    logger.exception("Unhandled exception on %s %s: %s", request.method, request.url, exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred. Please try again later.",
        },
    )
