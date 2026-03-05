import firebase_admin
from firebase_admin import credentials, firestore, storage, auth
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize Firebase
cred_path = os.getenv('FIREBASE_CREDENTIALS', 'firebase-credentials.json')

try:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)
    print("✅ Firebase initialized successfully")
except Exception as e:
    print(f"❌ Firebase initialization error: {e}")
    raise

# Get Firebase services
db = firestore.client()
auth_client = auth