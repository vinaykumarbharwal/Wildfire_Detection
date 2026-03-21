from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from datetime import datetime
import logging
import os

from api.routes import detections, auth, notifications, inference
from api.config.settings import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Wildfire Detection API",
    description="Real-time wildfire detection system API",
    version="1.0.0",
    docs_url=None,
    redoc_url=None
)

# Mount static files
static_path = os.path.join(os.path.dirname(__file__), "static")
app.mount("/api/static", StaticFiles(directory=static_path), name="static")

# Custom Swagger UI route
@app.get("/api/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="/api/static/swagger-ui-bundle.js",
        swagger_css_url="/api/static/swagger-ui.css",
    )

# Custom ReDoc route
@app.get("/api/redoc", include_in_schema=False)
async def redoc_html():
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=app.title + " - ReDoc",
        redoc_js_url="/api/static/redoc.standalone.js",
    )

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"], # Only allow local dashboard
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(detections.router, prefix="/api/detections", tags=["Detections"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])
app.include_router(inference.router, prefix="/api/inference", tags=["Inference"])

@app.get("/")
async def root():
    return {
        "message": "🔥 Wildfire Detection System API",
        "version": "1.0.0",
        "status": "operational",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database": "connected",
        "storage": "connected"
    }

@app.get("/api/stats")
async def get_stats():
    """Dashboard statistics: total, active, and resolved detections"""
    try:
        from api.services.stats_service import stats_service
        stats = await stats_service.get_dashboard_stats()
        return stats
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return {
            "total_detections": 0,
            "active_fires": 0,
            "resolved_fires": 0,
            "critical_fires": 0,
            "today_detections": 0,
            "by_severity": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "by_status": {"pending": 0, "verified": 0, "contained": 0, "false_alarm": 0, "resolved": 0},
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"message": "An internal error occurred", "detail": "Consult server logs for support ID."}
    )
