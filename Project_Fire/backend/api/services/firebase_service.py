import base64
import json
import logging
import os

import firebase_admin
from dotenv import load_dotenv
from firebase_admin import auth, credentials, firestore

load_dotenv()

logger = logging.getLogger(__name__)


class _UnavailableFirebase:
    """Guard object that raises a clear error when Firebase is not configured."""

    def __getattr__(self, name):
        raise RuntimeError(
            "Firebase is not configured. Set FIREBASE_CREDENTIALS or FIREBASE_CREDENTIALS_JSON."
        )


class _UnavailableFirestore:
    """Guard object that raises a clear error when Firestore is accessed without setup."""

    def collection(self, *args, **kwargs):
        raise RuntimeError(
            "Firestore is unavailable. Configure FIREBASE_CREDENTIALS or FIREBASE_CREDENTIALS_JSON."
        )


def _load_firebase_certificate():
    """Load Firebase cert from file path or JSON env (raw JSON or base64)."""
    # 1) File path (best for local/dev)
    if os.path.exists(cred_path):
        return credentials.Certificate(cred_path)

    # 2) JSON content from env (best for Render secrets)
    json_env = os.getenv("FIREBASE_CREDENTIALS_JSON", "").strip()
    if not json_env:
        return None

    try:
        parsed = json.loads(json_env)
        return credentials.Certificate(parsed)
    except json.JSONDecodeError:
        try:
            decoded = base64.b64decode(json_env).decode("utf-8")
            parsed = json.loads(decoded)
            return credentials.Certificate(parsed)
        except Exception:
            logger.exception("Invalid FIREBASE_CREDENTIALS_JSON format.")
            return None
    except Exception:
        logger.exception("Failed to parse Firebase credential JSON.")
        return None

# Initialize Firebase
# Try to find credentials relative to this script
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
default_cred_path = os.path.join(BASE_DIR, 'firebase-credentials.json')
cred_path = os.getenv('FIREBASE_CREDENTIALS', default_cred_path)

try:
    if not firebase_admin._apps:
        cert = _load_firebase_certificate()
        if cert:
            firebase_admin.initialize_app(cert)
            logger.info("Firebase initialized successfully.")
        else:
            logger.warning(
                "Firebase credentials not found. Running with Firebase-disabled mode."
            )
    else:
        logger.info("Firebase already initialized.")
except Exception:
    logger.exception("Firebase initialization error. Running with Firebase-disabled mode.")

# Get Firebase services
if firebase_admin._apps:
    db = firestore.client()
    auth_client = auth
else:
    db = _UnavailableFirestore()
    auth_client = _UnavailableFirebase()