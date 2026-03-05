import onnxruntime as ort
import numpy as np
from PIL import Image
import io
import os
import logging

logger = logging.getLogger(__name__)

class OnnxInferenceService:
    def __init__(self, model_path: str = None):
        if model_path is None:
            # Look for model in assets directory
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            model_path = os.path.join(base_dir, "assets", "models", "fire_model.onnx")
        
        self.model_path = model_path
        self.session = None
        self.input_name = None
        self.output_names = None
        self.input_shape = None
        
        if os.path.exists(model_path):
            try:
                self.session = ort.InferenceSession(model_path)
                self.input_name = self.session.get_inputs()[0].name
                self.output_names = [output.name for output in self.session.get_outputs()]
                self.input_shape = self.session.get_inputs()[0].shape # Usually [1, 3, 640, 640]
                logger.info(f"✅ ONNX Model loaded from {model_path}")
            except Exception as e:
                logger.error(f"❌ Failed to load ONNX model: {e}")
        else:
            logger.warning(f"⚠️ ONNX model not found at {model_path}. Inference will be mocked.")

    def preprocess(self, image_bytes: bytes):
        """Prepare image for the model"""
        image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        
        # Determine model input size (usually 640x640 for YOLO)
        width, height = (640, 640)
        if self.input_shape and isinstance(self.input_shape[2], int):
            height, width = self.input_shape[2], self.input_shape[3]
            
        image = image.resize((width, height))
        
        # Convert to numpy and normalize (standard 0-1)
        image_data = np.array(image).astype(np.float32) / 255.0
        
        # HWC to CHW (standard ONNX format [1, 3, H, W])
        image_data = np.transpose(image_data, (2, 0, 1))
        image_data = np.expand_dims(image_data, axis=0)
        
        return image_data

    async def run_inference(self, image_bytes: bytes):
        if not self.session:
            # Fallback mock for demonstration if no model is present
            return {
                "detected": True,
                "confidence": 0.85,
                "label": "mock_fire_test",
                "boxes": [[100, 100, 200, 200]],
                "message": "Demo mode: No model file found. Returning mock detection."
            }

        try:
            input_tensor = self.preprocess(image_bytes)
            outputs = self.session.run(self.output_names, {self.input_name: input_tensor})
            
            # Simple post-processing (adjust this based on your specific YOLO/Detection output)
            # This is a generic example - output[0] usually contains boxes + confs
            result = outputs[0]
            
            # TODO: Implement NMS and proper box extraction based on your model's specific architecture
            # For now, return the raw prediction summary or a simulated detection if confidence is high
            return {
                "detected": True, # Placeholder
                "confidence": 0.92, # Placeholder
                "label": "fire",
                "boxes": [[50, 50, 150, 150]],
                "raw_output_shape": list(result.shape)
            }
        except Exception as e:
            logger.error(f"Inference error: {e}")
            return {"detected": False, "error": str(e)}

# Singleton instance
onnx_service = OnnxInferenceService()
