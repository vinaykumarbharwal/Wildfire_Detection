from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class DetectionResponse(BaseModel):
    id: str
    latitude: float
    longitude: float
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    confidence: float
    image_url: str
    timestamp: datetime
    reported_by: Optional[str] = None
    status: str
    severity: str

class DetectionUpdate(BaseModel):
    status: Optional[str] = None
    severity: Optional[str] = None
    notes: Optional[str] = None

class DetectionCreate(BaseModel):
    latitude: float
    longitude: float
    confidence: float
    reported_by: Optional[str] = None
