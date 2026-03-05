import os
import json
from google.oauth2 import service_account
import google.auth.transport.requests

def get_access_token():
    # Path to your service account file
    # Ensure this matches your .env FIREBASE_CREDENTIALS
    creds_path = os.path.join(os.path.dirname(__file__), '..', 'backend', 'firebase-credentials.json')
    
    if not os.path.exists(creds_path):
        print(f"❌ Error: Service account file not found at {creds_path}")
        return

    # Define the scope for FCM
    SCOPES = ['https://www.googleapis.com/auth/firebase.messaging']

    # Load credentials
    credentials = service_account.Credentials.from_service_account_file(
        creds_path, scopes=SCOPES
    )

    # Refresh credentials to get the access token
    request = google.auth.transport.requests.Request()
    credentials.refresh(request)

    print("\n✅ Success! Copy the token below into your .env file:")
    print("-" * 20)
    print(credentials.token)
    print("-" * 20)
    print("\nNote: This token expires in 1 hour.")

if __name__ == "__main__":
    get_access_token()
