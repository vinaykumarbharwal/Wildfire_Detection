from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, List
from datetime import datetime, timedelta
import uuid
import shutil
import os

from api.services.firebase_service import db
from api.services.supabase_service import supabase_service
from api.services.notification_service import NotificationService
from api.services.geocoding_service import get_location_details, find_nearby_stations
from api.routes.auth import get_current_user
from api.models.detection import DetectionResponse, DetectionUpdate, DetectionCreate

async def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))):
    """Optional auth: returns user if token provided, else returns None"""
    if credentials is None:
        return None
    try:
        from api.routes.auth import get_current_user_from_token
        return await get_current_user_from_token(credentials.credentials)
    except Exception:
        return None

router = APIRouter()
notification_service = NotificationService()

# API routes starts here

@router.post("/report")
async def report_detection(
    latitude: float = Form(...),
    longitude: float = Form(...),
    confidence: float = Form(...),
    image: UploadFile = File(...),
    reported_by: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Report a new fire detection from mobile app (Authenticated)
    """
    try:
        # Validate inputs
        if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
            raise HTTPException(status_code=400, detail="Invalid coordinates")
        
        if not (0 <= confidence <= 1):
            raise HTTPException(status_code=400, detail="Confidence must be between 0 and 1")
        
        # Extract extension from uploaded file
        image_extension = image.filename.split('.')[-1] if '.' in image.filename else 'jpg'
        
        # Generate unique ID
        detection_id = str(uuid.uuid4())
        
        # Define image path for Supabase
        image_path = f"detections/{detection_id}.{image_extension}"
        
        # Save image temporarily
        import tempfile
        temp_dir = tempfile.gettempdir()
        temp_file = os.path.join(temp_dir, f"{detection_id}.{image_extension}")
        
        with open(temp_file, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        
        # Try to upload to Supabase (optional — detection still saves if this fails)
        image_url = None
        try:
            image_url = await supabase_service.upload_image(temp_file, image_path)
        except Exception as upload_err:
            print(f"⚠️ Image upload skipped (Supabase error): {upload_err}")
        finally:
            # Always clean up temp file
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception:
                pass
        
        # Get location details
        location_details = await get_location_details(latitude, longitude)
        
        # Find nearby fire stations
        nearby_stations = await find_nearby_stations(latitude, longitude)
        
        # Calculate severity based on confidence
        severity = "low"
        if confidence > 0.9:
            severity = "critical"
        elif confidence > 0.7:
            severity = "high"
        elif confidence > 0.5:
            severity = "medium"
        
        # Save to Firestore
        detection_data = {
            'id': detection_id,
            'latitude': latitude,
            'longitude': longitude,
            'address': location_details.get('address'),
            'city': location_details.get('city'),
            'state': location_details.get('state'),
            'country': location_details.get('country'),
            'postal_code': location_details.get('postal_code'),
            'confidence': confidence,
            'image_url': image_url,
            'timestamp': datetime.now(),
            'reported_by': current_user.get('uid'),
            'reporter_name': current_user.get('name'),
            'status': 'pending',
            'severity': severity,
            'nearby_stations': nearby_stations[:5],  # Top 5 nearest
            'notifications_sent': False
        }
        
        db.collection('detections').document(detection_id).set(detection_data)
        
        # Send notifications asynchronously
        await notification_service.send_alerts(detection_data, nearby_stations)
        
        # Update notification status
        db.collection('detections').document(detection_id).update({
            'notifications_sent': True,
            'notification_time': datetime.now()
        })
        
        return {
            "status": "success",
            "detection_id": detection_id,
            "message": "Fire reported successfully",
            "severity": severity,
            "image_url": image_url
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error reporting detection: {e}")
        raise HTTPException(status_code=500, detail="Internal processing error")

@router.get("/", response_model=List[DetectionResponse])
async def get_detections(
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = None,
    severity: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    """
    Get detections with filters
    """
    try:
        query = db.collection('detections').order_by('timestamp', direction='DESCENDING')
        
        if status:
            query = query.where('status', '==', status)
        
        if severity:
            query = query.where('severity', '==', severity)
        
        if start_date:
            query = query.where('timestamp', '>=', start_date)
        
        if end_date:
            query = query.where('timestamp', '<=', end_date)
        
        detections = query.limit(limit).stream()
        
        result = []
        for doc in detections:
            data = doc.to_dict()
            result.append(data)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/active")
async def get_active_detections():
    """Get all active (unresolved) fire detections"""
    try:
        active = db.collection('detections')\
                   .where('status', 'in', ['pending', 'verified'])\
                   .order_by('timestamp', direction='DESCENDING')\
                   .stream()
        
        result = []
        for doc in active:
            data = doc.to_dict()
            result.append(data)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{detection_id}")
async def get_detection(detection_id: str):
    """Get specific detection details"""
    try:
        doc = db.collection('detections').document(detection_id).get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Detection not found")
        
        return doc.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{detection_id}")
async def update_detection(
    detection_id: str,
    update_data: DetectionUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update detection status"""
    try:
        detection_ref = db.collection('detections').document(detection_id)
        detection = detection_ref.get()
        
        if not detection.exists:
            raise HTTPException(status_code=404, detail="Detection not found")
        
        update_dict = update_data.dict(exclude_unset=True)
        update_dict['updated_at'] = datetime.now()
        update_dict['updated_by'] = current_user.get('uid')
        
        detection_ref.update(update_dict)
        
        # If status changed to verified, send additional alerts
        if update_dict.get('status') == 'verified':
            await notification_service.send_verified_alert(detection.to_dict())
        
        return {"message": "Detection updated successfully", "id": detection_id}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{detection_id}/nearby-stations")
async def get_nearby_stations(detection_id: str):
    """Get fire stations near a detection"""
    try:
        doc = db.collection('detections').document(detection_id).get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Detection not found")
        
        data = doc.to_dict()
        stations = await find_nearby_stations(
            data['latitude'],
            data['longitude']
        )
        
        return stations
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))