import firebase_admin
from firebase_admin import credentials, firestore, storage, auth
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize Firebase
# Try to find credentials relative to this script
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
default_cred_path = os.path.join(BASE_DIR, 'firebase-credentials.json')
cred_path = os.getenv('FIREBASE_CREDENTIALS', default_cred_path)

try:
    if not firebase_admin._apps:
        if not os.path.exists(cred_path):
            raise FileNotFoundError(f"Firebase credentials not found at {cred_path}")
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        print(f"✅ Firebase initialized successfully from {cred_path}")
    else:
        print("ℹ️ Firebase already initialized")
except Exception as e:
    print(f"❌ Firebase initialization error: {e}")
    raise

# Get Firebase services
db = firestore.client()
auth_client = auth