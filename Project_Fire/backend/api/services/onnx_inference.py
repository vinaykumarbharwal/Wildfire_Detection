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
            # Default model location used by inference API.
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            model_path = os.path.join(base_dir, "models", "fire_model.onnx")
        
        self.model_path = model_path
        self.session = None
        self.input_name = None
        self.output_names = None
        self.input_shape = None
        self.confidence_threshold = float(os.getenv("FIRE_CONFIDENCE_THRESHOLD", "0.50"))
        
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
                "fire_detected": True,
                "confidence": 0.85,
                "label": "mock_fire_test",
                "boxes": [[100, 100, 200, 200]],
                "message": "Demo mode: No model file found. Returning mock detection."
            }

        try:
            input_tensor = self.preprocess(image_bytes)
            outputs = self.session.run(self.output_names, {self.input_name: input_tensor})
            
            # Parsing [1, 300, 6] output
            # Assuming format: [batch, num_boxes, [x, y, w, h, confidence, class_id]]
            predictions = outputs[0][0] # shape: (300, 6)
            
            # Find the best prediction (highest confidence)
            best_idx = np.argmax(predictions[:, 4])
            best_pred = predictions[best_idx]
            
            confidence = float(best_pred[4])
            detected = confidence > self.confidence_threshold
            
            logger.info(
                "Top ONNX prediction confidence: %.2f%% (Threshold: %.2f%%)",
                confidence * 100,
                self.confidence_threshold * 100,
            )
            
            return {
                "fire_detected": detected,
                "confidence": round(float(confidence), 4),
                "label": "fire" if detected else "none",
                "boxes": [best_pred[0:4].tolist()],
                "raw_output_shape": list(outputs[0].shape),
                "threshold": self.confidence_threshold,
            }
        except Exception as e:
            logger.error(f"Inference error: {e}")
            return {"fire_detected": False, "error": str(e)}

# Singleton instance
onnx_service = OnnxInferenceService()
