
import os
import asyncio
import numpy as np
from PIL import Image
import io
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
BACKEND_DIR = os.path.join(PROJECT_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from api.services.onnx_inference import OnnxInferenceService

async def test_inference():
    # Path to the model in this repository
    model_path = os.path.join(BACKEND_DIR, "api", "models", "fire_model.onnx")
    
    print(f"Checking model at: {model_path}")
    if not os.path.exists(model_path):
        print("❌ Model file not found!")
        return

    service = OnnxInferenceService(model_path)
    
    if not service.session:
        print("❌ Service failed to load model session.")
        return

    print("✅ Model session loaded successfully!")
    print(f"Input Name: {service.input_name}")
    print(f"Input Shape: {service.input_shape}")
    
    # Create a dummy image (RGB 640x640)
    dummy_image = Image.new('RGB', (640, 640), color=(255, 0, 0))
    img_byte_arr = io.BytesIO()
    dummy_image.save(img_byte_arr, format='JPEG')
    img_bytes = img_byte_arr.getvalue()
    
    print("Running inference...")
    try:
        results = await service.run_inference(img_bytes)
        print(f"Success! Results: {results}")
    except Exception as e:
        print(f"❌ Inference failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_inference())
