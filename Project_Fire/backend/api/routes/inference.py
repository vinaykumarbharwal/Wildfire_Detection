import os
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from api.services.onnx_inference import onnx_service
from api.services.firebase_service import db
from api.routes.detections import _upload_image
from api.services.notification_service import NotificationService
from datetime import datetime
import logging
import uuid

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
    """
    try:
        image_bytes = await image.read()

        # Run inference using the service
        results = await onnx_service.run_inference(image_bytes)

        # Sync the key: the service returns 'fire_detected'
        detected: bool = results.get("fire_detected", False)
        
        if detected:
            print(f"\n🚨 [FIRE DETECTED] !!! - Confidence: {results.get('confidence'):.2%}\n")
            
            # --- GLOBAL DASHBOARD SYNC ---
            detection_id = str(uuid.uuid4())
            
            # 📸 Upload the actual evidence photo
            image.file.seek(0) # Reset file pointer for re-reading
            image_url = await _upload_image(image, detection_id)
            
            detection_data = {
                "id": detection_id,
                "latitude": lat,
                "longitude": lng,
                "confidence": results.get("confidence", 0.0),
                "severity": _calculate_severity(results.get("confidence", 0.0)),
                "timestamp": datetime.utcnow().isoformat() + "Z", # ISO format for JS
                "status": "pending",
                "address": "Mobile Surveillance Node",
                "image_url": image_url or "https://raw.githubusercontent.com/vinaykumarbharwal/Fire_GITHUB/main/Project_Fire/mobile_app/flutter_app/assets/images/placeholder_fire.jpg"
            }
            db.collection("detections").document(detection_id).set(detection_data)
            print(f"📡 Broadcast to Global Dashboard Complete (ID: {detection_id})")

            # 🔥 TACTICAL DISPATCH PROTOCOL 🔥 
            # When confidence > 70%, trigger automated emergency response
            if results.get('confidence', 0.0) > 0.7:
                print("⚡ [TACTICAL DISPATCH] Initiating emergency phone and email alerts...")
                # 1. SMS to emergency responders
                await notification_service.send_verified_alert(detection_data)
                
                # 2. Evidence Email to mission control
                await notification_service.send_email(
                    to=os.getenv('EMAIL_USER'), # Sending to yourself for verification
                    detection=detection_data
                )
        else:
            print("✅ Area Clear.")
            
        confidence: float = float(results.get("confidence", 0.0))
        severity: str = results.get("severity") or _calculate_severity(confidence)

        return {
            "status": "success",
            "fire_detected": detected,
            "confidence": confidence,
            "severity": severity,
            "timestamp": results.get("timestamp", ""),
            "filename": image.filename
        }
    except Exception as e:
        logger.error(f"Inference API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

