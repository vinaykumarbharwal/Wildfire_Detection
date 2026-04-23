# Render Firebase Credentials

Use the Firebase service account JSON as a Render environment variable.

## Recommended setup
- Key: `FIREBASE_CREDENTIALS_JSON`
- Value: paste the full service account JSON from Firebase Console

## If Render rejects multiline JSON
Convert the JSON file to base64 and store that string in `FIREBASE_CREDENTIALS_JSON`.

## Important
- Do not commit the real credentials file to GitHub.
- Rotate any key that was already shared publicly.
- `firebase-credentials.example.json` is only a template and contains no secrets.
