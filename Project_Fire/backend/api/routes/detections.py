"""
detections.py – Detection routes for the Wildfire Detection API.

Endpoints:
  POST   /report                  – Report a new fire detection (auth required)
  GET    /                        – List all detections with optional filters
  GET    /active                  – Get all active (pending/verified) detections
  GET    /{detection_id}          – Get a single detection by ID
  PUT    /{detection_id}          – Update a detection's status/severity (auth required)
  DELETE /{detection_id}          – Delete a detection (auth required)
  GET    /{detection_id}/nearby-stations – Get fire stations near a detection
"""

import logging
import os
import shutil
import tempfile
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)

from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.models.detection import DetectionResponse, DetectionUpdate
from api.routes.auth import get_current_user
from api.services.firebase_service import db
from api.services.geocoding_service import find_nearby_stations, get_location_details
from api.services.notification_service import NotificationService
from api.services.supabase_service import supabase_service
from api.services.weather_service import get_current_weather
from api.services.llm_service import generate_tactical_report

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Router & shared services
# ──────────────────────────────────────────────
router = APIRouter()
notification_service = NotificationService()

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_SIZE_MB = 10


# ──────────────────────────────────────────────
# Helper – optional authentication
# ──────────────────────────────────────────────
async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
) -> Optional[dict]:
    """Returns the authenticated user dict if a valid token is supplied, otherwise None."""
    if credentials is None:
        return None
    try:
        from api.routes.auth import get_current_user_from_token

        return await get_current_user_from_token(credentials.credentials)
    except Exception:
        return None


# ──────────────────────────────────────────────
# Helper – severity calculation
# ──────────────────────────────────────────────
def _calculate_severity(confidence: float) -> str:
    if confidence > 0.9:
        return "critical"
    if confidence > 0.7:
        return "high"
    if confidence > 0.5:
        return "medium"
    return "low"

# ──────────────────────────────────────────────
# Background Task – heavy processing
# ──────────────────────────────────────────────
async def process_detection_task(
    detection_id: str,
    latitude: float,
    longitude: float,
    confidence: float,
    temp_image_path: str,
    user_uid: str,
    user_name: str,
):
    """
    Handles heavy I/O and processing in the background:
    1. Uploads image to Supabase.
    2. Gathers geocoding, weather, and nearby stations.
    3. Persists the final record to Firestore.
    4. Dispatches emergency notifications.
    """
    try:
        # 1. Upload image to Supabase
        image_url = None
        if os.path.exists(temp_image_path):
            ext = temp_image_path.rsplit(".", 1)[-1].lower()
            supabase_path = f"detections/{detection_id}.{ext}"
            try:
                image_url = await supabase_service.upload_image(temp_image_path, supabase_path)
            except Exception as exc:
                logger.error("Supabase upload failed for %s: %s", detection_id, exc)

        # 2. Gather rich metadata
        location_details, nearby_stations, weather_data = await _gather_location_data(
            latitude, longitude
        )
        severity = _calculate_severity(confidence)

        # 3. Construct detection object
        detection_data = {
            "id": detection_id,
            "latitude": latitude,
            "longitude": longitude,
            "address": location_details.get("address"),
            "city": location_details.get("city"),
            "state": location_details.get("state"),
            "country": location_details.get("country"),
            "postal_code": location_details.get("postal_code"),
            "confidence": round(confidence, 4),
            "image_url": image_url,
            "timestamp": datetime.utcnow(),
            "reported_by": user_uid,
            "reporter_name": user_name,
            "status": "pending",
            "severity": severity,
            "nearby_stations": nearby_stations[:5],
            "weather_snapshot": weather_data,
            "notifications_sent": False,
            "notes": None,
            "ai_tactical_report": None  # Placeholder
        }

        # 4. Automated AI Tactical Analysis (New)
        # For High/Critical threats, pre-generate the report for immediate response
        if severity in ["high", "critical"]:
            try:
                logger.info("⚡ Generating proactive AI tactical report for %s", detection_id)
                ai_report = await generate_tactical_report(detection_data)
                detection_data["ai_tactical_report"] = ai_report
            except Exception as ai_exc:
                logger.error("Proactive AI report failed: %s", ai_exc)

        # 5. Save to Firestore
        db.collection("detections").document(detection_id).set(detection_data)
        logger.info("Background processing complete for %s (severity=%s)", detection_id, severity)

        # 5. Send notifications
        try:
            await notification_service.send_alerts(detection_data, nearby_stations)
            db.collection("detections").document(detection_id).update(
                {
                    "notifications_sent": True,
                    "notification_time": datetime.utcnow(),
                }
            )
        except Exception as notif_err:
            logger.error("Notification error for %s: %s", detection_id, notif_err)

    except Exception as exc:
        logger.exception("Critical error in background task for %s: %s", detection_id, exc)
    finally:
        # Cleanup temp file
        if os.path.exists(temp_image_path):
            try:
                os.remove(temp_image_path)
            except OSError:
                pass


# ══════════════════════════════════════════════
# POST /report – Report a new fire detection
# ══════════════════════════════════════════════
@router.post("/report", status_code=status.HTTP_201_CREATED)
async def report_detection(
    background_tasks: BackgroundTasks,
    latitude: float = Form(...),
    longitude: float = Form(...),
    confidence: float = Form(...),
    image: UploadFile = File(...),
    reported_by: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user),
):
    """
    Report a new fire detection. 
    Returns 201 Created immediately after queuing the detection for background processing.
    """

    # ── Validate inputs ──────────────────────
    if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid coordinates – latitude must be in [-90, 90] and longitude in [-180, 180].",
        )

    if not (0.0 <= confidence <= 1.0):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Confidence must be a float between 0.0 and 1.0.",
        )

    if image.content_type and image.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported image type '{image.content_type}'. Allowed: {ALLOWED_IMAGE_TYPES}",
        )

    try:
        detection_id = str(uuid.uuid4())

        # ── Save image to a temporary file immediately ──
        # We must save the stream before the request finishes
        ext = (
            image.filename.rsplit(".", 1)[-1].lower()
            if image.filename and "." in image.filename
            else "jpg"
        )
        temp_file = os.path.join(tempfile.gettempdir(), f"{detection_id}.{ext}")
        
        with open(temp_file, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)

        # ── Queue heavy lifting for later ──
        background_tasks.add_task(
            process_detection_task,
            detection_id=detection_id,
            latitude=latitude,
            longitude=longitude,
            confidence=confidence,
            temp_image_path=temp_file,
            user_uid=current_user.get("uid"),
            user_name=current_user.get("name")
        )

        return {
            "status": "queued",
            "detection_id": detection_id,
            "message": "Detection report received and queued for processing.",
            "estimated_processing_time": "3-5 seconds",
        }

    except Exception as exc:
        logger.exception("Queueing detection failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to queue detection report.",
        )



async def _gather_location_data(latitude: float, longitude: float):
    """Run reverse-geocoding and station lookup, returning empty defaults on failure."""
    try:
        location_details = await get_location_details(latitude, longitude)
    except Exception as exc:
        logger.warning("Geocoding failed: %s", exc)
        location_details = {}

    try:
        nearby_stations = await find_nearby_stations(latitude, longitude)
    except Exception as exc:
        logger.warning("Nearby station lookup failed: %s", exc)
        nearby_stations = []

    try:
        weather_data = await get_current_weather(latitude, longitude)
    except Exception as exc:
        logger.warning("Weather metrics fetch failed: %s", exc)
        weather_data = {}

    return location_details, nearby_stations, weather_data


# ══════════════════════════════════════════════
# GET / – List detections with optional filters
# ══════════════════════════════════════════════
@router.get("/", response_model=List[DetectionResponse])
async def get_detections(
    limit: int = Query(100, ge=1, le=1000, description="Max number of records to return"),
    status: Optional[str] = Query(None, description="Filter by status"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    start_date: Optional[datetime] = Query(None, description="Only return detections after this datetime"),
    end_date: Optional[datetime] = Query(None, description="Only return detections before this datetime"),
):
    """Retrieve detections with optional filters."""
    try:
        query = db.collection("detections").order_by(
            "timestamp", direction="DESCENDING"
        )

        if status:
            query = query.where("status", "==", status)
        if severity:
            query = query.where("severity", "==", severity)
        if start_date:
            query = query.where("timestamp", ">=", start_date)
        if end_date:
            query = query.where("timestamp", "<=", end_date)

        docs = query.limit(limit).stream()
        return [doc.to_dict() for doc in docs]

    except Exception as exc:
        logger.exception("Error fetching detections: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve detections.",
        )


# ══════════════════════════════════════════════
# GET /active – Active (unresolved) detections
# ══════════════════════════════════════════════
@router.get("/active")
async def get_active_detections():
    """Get all active (pending or verified) fire detections."""
    try:
        docs = (
            db.collection("detections")
            .where("status", "in", ["pending", "verified"])
            .order_by("timestamp", direction="DESCENDING")
            .stream()
        )
        return [doc.to_dict() for doc in docs]

    except Exception as exc:
        logger.exception("Error fetching active detections: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve active detections.",
        )


# ══════════════════════════════════════════════
# GET /{detection_id} – Single detection
# ══════════════════════════════════════════════
@router.get("/{detection_id}")
async def get_detection(detection_id: str):
    """Get a specific detection record by its ID."""
    try:
        doc = db.collection("detections").document(detection_id).get()

        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Detection '{detection_id}' not found.",
            )

        return doc.to_dict()

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error fetching detection %s: %s", detection_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve detection.",
        )


# ══════════════════════════════════════════════
# PUT /{detection_id} – Update detection
# ══════════════════════════════════════════════
@router.put("/{detection_id}")
async def update_detection(
    detection_id: str,
    update_data: DetectionUpdate,
):
    """Update a detection's status, severity, or notes."""
    try:
        detection_ref = db.collection("detections").document(detection_id)
        detection_snap = detection_ref.get()

        if not detection_snap.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Detection '{detection_id}' not found.",
            )

        update_dict = update_data.dict(exclude_unset=True)
        update_dict["updated_at"] = datetime.utcnow()
        update_dict["updated_by"] = "Admin_Desk"

        detection_ref.update(update_dict)
        logger.info(
            "Detection %s updated by Admin_Desk: %s",
            detection_id,
            update_dict,
        )

        # Send additional alert when status is verified
        if update_dict.get("status") == "verified":
            try:
                await notification_service.send_verified_alert(detection_snap.to_dict())
            except Exception as notif_err:
                logger.error(
                    "Verified alert notification failed for %s: %s",
                    detection_id,
                    notif_err,
                )

        return {"message": "Detection updated successfully.", "id": detection_id}

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error updating detection %s: %s", detection_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update detection.",
        )


# ══════════════════════════════════════════════
# DELETE /{detection_id} – Delete detection
# ══════════════════════════════════════════════
@router.delete("/{detection_id}", status_code=status.HTTP_200_OK)
async def delete_detection(
    detection_id: str,
):
    """Permanently delete a detection record (authentication required)."""
    try:
        detection_ref = db.collection("detections").document(detection_id)

        if not detection_ref.get().exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Detection '{detection_id}' not found.",
            )

        detection_ref.delete()
        logger.info(
            "Detection %s deleted via Admin Hub.", detection_id
        )
        return {"message": "Detection deleted successfully.", "id": detection_id}

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error deleting detection %s: %s", detection_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete detection.",
        )


# ══════════════════════════════════════════════
# GET /{detection_id}/nearby-stations
# ══════════════════════════════════════════════
@router.get("/{detection_id}/nearby-stations")
async def get_nearby_stations(detection_id: str):
    """Return fire stations nearest to the specified detection location."""
    try:
        doc = db.collection("detections").document(detection_id).get()

        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Detection '{detection_id}' not found.",
            )

        data = doc.to_dict()
        stations = await find_nearby_stations(data["latitude"], data["longitude"])
        return stations

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(
            "Error fetching nearby stations for %s: %s", detection_id, exc
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve nearby stations.",
        )


# ══════════════════════════════════════════════
# AI Tactical Report Generator
# ══════════════════════════════════════════════
@router.post("/{detection_id}/generate-ai-report", tags=["Detections"])
async def generate_ai_report_endpoint(detection_id: str):
    """
    On-demand AI Tactical Report Generation using Google Gemini.
    Reads the detection data from Firestore and passes it to the LLM.
    The generated report is saved back to the document and returned.
    """
    from api.services.llm_service import generate_tactical_report

    try:
        detection_ref = db.collection("detections").document(detection_id)
        doc = detection_ref.get()
        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Detection '{detection_id}' not found.",
            )

        data = doc.to_dict()

        # Call the Gemini service
        report = await generate_tactical_report(data)

        # Persist the report to avoid re-generating on every refresh
        detection_ref.update({"ai_tactical_report": report})

        return {"status": "success", "detection_id": detection_id, "ai_tactical_report": report}

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("AI report generation failed for %s: %s", detection_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI report generation failed: {str(exc)}",
        )