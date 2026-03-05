from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from api.services.firebase_service import db
from api.routes.auth import get_current_user

router = APIRouter()

class NotificationResponse(BaseModel):
    id: str
    title: str
    body: str
    detection_id: Optional[str] = None
    timestamp: datetime
    type: str  # alert, info, verification
    is_read: bool = False

@router.get("/", response_model=List[NotificationResponse])
async def get_notifications(
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_user)
):
    """
    Get notification history for the current user
    """
    try:
        # For simplicity, we fetch notifications from 'notifications' collection
        # filtered by user_id if applicable, or general alerts
        notifications_ref = db.collection('notifications')\
                            .order_by('timestamp', direction='DESCENDING')\
                            .limit(limit)
        
        docs = notifications_ref.stream()
        
        result = []
        for doc in docs:
            data = doc.to_dict()
            result.append(data)
            
        return result
        
    except Exception as e:
        print(f"Error fetching notifications: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{notification_id}/read")
async def mark_as_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Mark a notification as read
    """
    try:
        notification_ref = db.collection('notifications').document(notification_id)
        doc = notification_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Notification not found")
            
        notification_ref.update({'is_read': True})
        return {"message": "Notification marked as read"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
