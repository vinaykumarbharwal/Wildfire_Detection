import os
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from api.services.onnx_inference import onnx_service
from api.services.firebase_service import db
from api.services.supabase_service import supabase_service
from api.services.notification_service import NotificationService
from api.services.geocoding_service import get_location_details
from datetime import datetime
import logging
import uuid
import tempfile
import shutil

# Initialize tactical services
notification_service = NotificationService()

router = APIRouter()
logger = logging.getLogger(__name__)


def _calculate_severity(confidence: float) -> str:
    if confidence > 0.9:
        return "critical"
    if confidence > 0.7:
        return "high"
    if confidence > 0.5:
        return "medium"
    return "low"


@router.post("/detect")
async def detect_fire(
    image: UploadFile = File(...),
    lat: float = Form(0.0),
    lng: float = Form(0.0)
):
    """
    Run ONNX inference and save detection to Firestore if fire is confirmed.
    Geocodes real GPS coordinates from mobile app into a readable address.
    """
    address = "Mobile Surveillance Node"
    city = None
    state = None
    country = None

    try:
        image_bytes = await image.read()

        # Run inference
        results = await onnx_service.run_inference(image_bytes)
        detected: bool = results.get("fire_detected", False)

        if detected:
            confidence_val = results.get("confidence", 0.0)
            print(f"\n🚨 [FIRE DETECTED] Confidence: {confidence_val:.2%} | GPS: {lat}, {lng}\n")

            detection_id = str(uuid.uuid4())

            # ── Upload evidence photo ──
            ext = image.filename.rsplit(".", 1)[-1].lower() if "." in (image.filename or "") else "jpg"
            supabase_path = f"detections/{detection_id}.{ext}"
            
            # Save stream to a temp file for Supabase upload
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
                image.file.seek(0)
                shutil.copyfileobj(image.file, tmp)
                tmp_path = tmp.name
            
            image_url = None
            try:
                image_url = await supabase_service.upload_image(tmp_path, supabase_path)
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

            # 📍 Reverse-geocode real GPS coordinates
            address = "Mobile Surveillance Node"
            city = None
            state = None
            country = None

            if lat != 0.0 or lng != 0.0:
                try:
                    loc_details = await get_location_details(lat, lng)
                    address = loc_details.get("address") or address
                    city    = loc_details.get("city")
                    state   = loc_details.get("state")
                    country = loc_details.get("country")
                    logger.info(f"📍 Geocoded: {address}, {city}, {state}, {country}")
                except Exception as geo_err:
                    logger.warning(f"Geocoding skipped (will use fallback): {geo_err}")

            detection_data = {
                "id": detection_id,
                "latitude": lat,
                "longitude": lng,
                "confidence": confidence_val,
                "severity": _calculate_severity(confidence_val),
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "status": "pending",
                "address": address,
                "city": city,
                "state": state,
                "country": country,
                "image_url": image_url or "https://raw.githubusercontent.com/vinaykumarbharwal/Fire_GITHUB/main/Project_Fire/mobile_app/flutter_app/assets/images/placeholder_fire.jpg"
            }

            db.collection("detections").document(detection_id).set(detection_data)
            logger.info(f"📡 Firestore sync complete | ID: {detection_id} | Address: {address}")

            # 🔥 Tactical Dispatch — alert if confidence > 70%
            if confidence_val > 0.7:
                logger.info("⚡ [TACTICAL DISPATCH] Sending emergency alerts...")
                try:
                    await notification_service.send_verified_alert(detection_data)
                except Exception as notif_err:
                    logger.error(f"Alert dispatch failed: {notif_err}")

                try:
                    await notification_service.send_email(
                        to=os.getenv('EMAIL_USER'),
                        detection=detection_data
                    )
                except Exception as email_err:
                    logger.error(f"Email dispatch failed: {email_err}")
        else:
            print("✅ Area Clear — No fire detected.")

        confidence: float = float(results.get("confidence", 0.0))
        severity: str = results.get("severity") or _calculate_severity(confidence)

        return {
            "status": "success",
            "fire_detected": detected,
            "confidence": confidence,
            "severity": severity,
            "timestamp": results.get("timestamp", ""),
            "filename": image.filename,
            "location": {
                "latitude": lat,
                "longitude": lng,
                "address": address if detected else None
            }
        }

    except Exception as e:
        logger.error(f"Inference API error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
