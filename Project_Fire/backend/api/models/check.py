import streamlit as st
import numpy as np
from PIL import Image
import os
import sys
import asyncio

# 🧬 Add the backend directory to sys.path to import our service
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from api.services.onnx_inference import OnnxInferenceService

# ── STREAMLIT PAGE CONFIG ──────────────────────
st.set_page_config(
    page_title="Agniveer AI - Model Inspector",
    page_icon="🔥",
    layout="wide"
)

# ── STYLING ──────────────────────
st.markdown("""
<style>
    .main {
        background-color: #0d1117;
        color: #e6edf3;
    }
    .stHeader {
        background: linear-gradient(135deg, #ff4c4c, #ff9068);
        border-radius: 10px;
        padding: 20px;
        color: white !important;
        text-align: center;
        margin-bottom: 30px;
    }
    .status-card {
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="stHeader"><h1>🔥 Agniveer AI Model Inspector</h1><p>Upload a photo to see the detection result in real-time.</p></div>', unsafe_allow_html=True)

# ── MODEL INITIALIZATION ──────────────────────
@st.cache_resource
def load_model():
    # Automatically finds it at api/models/fire_model.onnx
    return OnnxInferenceService()

detector = load_model()

# ── UI LAYOUT ──────────────────────
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📸 Image Input")
    source = st.radio("Choose source:", ["Take Photo", "Upload File"], horizontal=True)
    
    img_file = None
    if source == "Take Photo":
        img_file = st.camera_input("Smile at the detector!")
    else:
        img_file = st.file_uploader("Drop fire image here...", type=["jpg", "jpeg", "png", "webp"])

    if img_file:
        image = Image.open(img_file)
        st.image(image, caption="Current Input", use_container_width=True)

with col2:
    st.subheader("🧬 AI Prediction Output")
    
    if img_file:
        with st.spinner("AI is analyzing the frame..."):
            # ── 1. Create a byte Buffer ──────
            import io
            buf = io.BytesIO()
            image.save(buf, format="JPEG")
            byte_content = buf.getvalue()

            # ── 2. Run Inference (Awaiting the async service) ──────
            result = asyncio.run(detector.run_inference(byte_content))

        # ── 3. Display Results ──────
        if result["fire_detected"]:
            st.error(f"🚨 FIRE DETECTED! (Confidence: {result['confidence']:.2%})")
            
            # Show Bounding Box Stats
            if result.get("boxes"):
                st.table(result["boxes"])
        else:
            st.success("✅ Area Clear. No fire signatures found.")
            st.metric("Detection Score", f"{result['confidence']:.2%}")
            
        # 🔗 Backend Path Indicator:
        st.info(f"Using Model At: {detector.model_path}")
    else:
        st.info("👈 Please capture or upload a frame to begin.")

# ── FOOTER ──────────────────────
st.markdown("---")
st.caption("Agniveer DeepMind Wildfire Surveillance • 2026")
