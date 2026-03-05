from fastapi import APIRouter, UploadFile, File, HTTPException
from api.services.onnx_inference import onnx_service
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/detect")
async def detect_fire(image: UploadFile = File(...)):
    """
    Run ONNX inference on an uploaded image
    """
    try:
        image_bytes = await image.read()
        
        # Run inference using the service
        results = await onnx_service.run_inference(image_bytes)
        
        return {
            "status": "success",
            "results": results,
            "filename": image.filename
        }
    except Exception as e:
        logger.error(f"Inference API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
