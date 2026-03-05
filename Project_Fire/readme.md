# 🔥 Agniveer — Wildfire Detection & Surveillance System

> An end-to-end real-time wildfire detection platform powered by on-device AI, FastAPI, Firebase, and n8n automation. Detects fires through mobile cameras, alerts nearby fire stations, and visualizes detections on a live web dashboard.

---

## 📋 Table of Contents
- [Features](#-features)
- [System Architecture](#-system-architecture)
- [Technology Stack](#-technology-stack)
- [Project Structure](#-project-structure)
- [Quick Start with Docker](#-quick-start-with-docker)
- [Manual Setup](#-manual-setup)
  - [1. Environment Variables](#1-environment-variables)
  - [2. Firebase Setup](#2-firebase-setup)
  - [3. Backend API](#3-backend-api)
  - [4. Frontend Website](#4-frontend-website)
  - [5. Flutter Mobile App](#5-flutter-mobile-app)
  - [6. n8n Automation](#6-n8n-automation)
- [API Reference](#-api-reference)
- [Mobile App Build](#-mobile-app-build)
- [Configuration](#-configuration)
- [Troubleshooting](#-troubleshooting)

---

## ✨ Features

| Component | Capabilities |
|-----------|-------------|
| 📱 **Mobile App** | Real-time TFLite fire detection, GPS capture, instant alerts, detection history |
| ⚙️ **Backend API** | FastAPI with JWT auth, geocoding, Supabase image storage, FCM push notifications |
| 🌐 **Web Dashboard** | Live Leaflet map, real-time Firebase listener, dark/light mode, charts, filters |
| 📨 **Alert System** | Multi-channel SMS (Twilio), Email (SMTP), Push (FCM), nearest station lookup |
| 🤖 **Automation** | n8n workflows for fire alerts and station notifications with permanent credentials |
| 🐳 **Docker** | One-command deployment for backend, frontend (nginx), and n8n |

---

## 🏗️ System Architecture

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   Flutter App    │────▶│  FastAPI Backend  │────▶│    Firebase      │
│ (TFLite + GPS)   │     │  (Auth, Detect,   │     │ (Firestore +     │
│                  │◀────│   Notifications)  │◀────│  FCM)            │
└──────────────────┘     └──────────────────┘     └──────────────────┘
         │                        │                        │
         │                        │                        │
         ▼                        ▼                        ▼
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   GPS Location   │     │  n8n Workflows   │     │ Web Dashboard    │
│   (Coordinates)  │     │  (SMS + Email    │     │ (Leaflet Map +   │
│                  │     │   Automation)    │     │  Charts)         │
└──────────────────┘     └──────────────────┘     └──────────────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │ Supabase Storage │
                         │ (Detection       │
                         │  Images)         │
                         └──────────────────┘
```

---

## 🛠️ Technology Stack

| Layer | Technology |
|-------|-----------|
| Mobile | Flutter, TFLite (YOLOv8), Provider, Camera |
| Backend | Python 3.11, FastAPI, Firebase Admin SDK |
| Database | Google Firestore (real-time NoSQL) |
| Storage | Supabase Storage (detection images) |
| Auth | Firebase Auth + JWT (HS256) |
| Notifications | Twilio SMS, SMTP Email, FCM Push |
| Frontend | HTML, Tailwind CSS, Leaflet.js, Chart.js |
| Automation | n8n (self-hosted workflow engine) |
| Infrastructure | Docker, nginx, Docker Compose |

---

## 📁 Project Structure

```
Project_Fire/
├── backend/                    # Python FastAPI server
│   ├── api/
│   │   ├── config/settings.py  # Central configuration (pydantic-settings)
│   │   ├── models/detection.py # Pydantic request/response models
│   │   ├── routes/             # API endpoints (auth, detections, notifications)
│   │   └── services/           # Firebase, Supabase, geocoding, notifications
│   ├── firebase-credentials.json
│   └── .env                    # Your secrets (copy from config/.env.example)
│
├── frontend_website/           # Web surveillance dashboard
│   ├── index.html              # Main SPA (Tailwind + Leaflet + Chart.js)
│   └── js/
│       ├── main.js             # App logic (IIFE-encapsulated)
│       └── map.js              # MapController (Leaflet, light/dark tiles)
│
├── mobile_app/flutter_app/    # Flutter mobile detection app
│   └── lib/
│       ├── main.dart           # App entry + MultiProvider setup
│       ├── providers/          # DashboardProvider (state management)
│       ├── screens/            # Camera, Dashboard, Login, History
│       └── services/           # DetectionService (TFLite), ApiService
│
├── automation/                 # n8n workflow automation
│   ├── n8n_workflows/          # fire-alert.json, station-notification.json
│   └── N8N_PERMANENT_SETUP.md  # Guide for setting up permanent FCM credentials
│
├── database/firebase/          # Firebase security rules
│   ├── firestore.rules
│   └── storage.rules
│
├── docker/                     # Docker configuration
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   ├── docker-compose.yml      # All 3 services (backend, frontend, n8n)
│   └── nginx.conf
│
├── config/
│   └── .env.example            # Template for all required environment variables
│
└── scripts/
    └── get_token.py            # Utility: generate a short-lived FCM token (legacy)
```

---

## 🐳 Quick Start with Docker

> **Fastest way** to run the entire stack.

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/vinaykumarbharwal/Project_Fire.git
cd Project_Fire

# 2. Create your environment file
copy config\.env.example backend\.env
# Then EDIT backend\.env with your real credentials

# 3. Start everything
cd docker
docker-compose up --build
```

### Running Services

| Service | URL |
|---------|-----|
| 🌐 Web Dashboard | http://localhost:80 |
| ⚙️ API & Docs | http://localhost:8000/api/docs |
| 🤖 n8n Automation | http://localhost:5678 |

---

## 🔧 Manual Setup

### 1. Environment Variables

Copy the template and fill in your credentials:

```bash
copy config\.env.example backend\.env
```

**Required variables:**

```env
# Firebase
FIREBASE_CREDENTIALS=firebase-credentials.json
FIREBASE_PROJECT_ID=your-project-id

# Supabase (Image Storage)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_BUCKET_NAME=detections

# Twilio (SMS Alerts)
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=+1234567890

# Email Alerts
EMAIL_USER=your_email@gmail.com
EMAIL_PASSWORD=your_gmail_app_password

# Security
JWT_SECRET_KEY=change_this_to_a_random_secret_string

# Google Maps (Geocoding + Station Lookup)
GOOGLE_MAPS_API_KEY=your_google_maps_api_key

# n8n
N8N_PASSWORD=your_n8n_admin_password

# Emergency Contacts
EMERGENCY_PHONE_NUMBERS=+91XXXXXXXXXX,+91XXXXXXXXXX
```

---

### 2. Firebase Setup

1. Go to [Firebase Console](https://console.firebase.google.com/) and create a project
2. Enable **Firestore Database** and **Authentication** (Email/Password)
3. Go to **Project Settings → Service Accounts** → Generate a new private key
4. Save the downloaded file as `backend/firebase-credentials.json`
5. Deploy the security rules:

```bash
firebase deploy --only firestore:rules
firebase deploy --only storage:rules
```

---

### 3. Backend API

```bash
cd backend
pip install -r requirements.txt
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

Visit **http://localhost:8000/api/docs** for interactive API documentation.

---

### 4. Frontend Website

```bash
cd frontend_website
python -m http.server 3000
# Visit: http://localhost:3000
```

Or simply open `frontend_website/index.html` directly in a browser.

---

### 5. Flutter Mobile App

#### Prerequisites
- Flutter SDK 3.x installed (`flutter doctor` to verify)
- Android Studio + Android SDK or Xcode (for iOS)

#### Setup Steps

```bash
cd mobile_app/flutter_app
flutter pub get
```

**Place your trained TFLite model:**
```
mobile_app/flutter_app/assets/models/your_trained_model.tflite
```

**Update the API URL** in `lib/services/api_service.dart`:
```dart
static const String baseUrl = 'http://YOUR_SERVER_IP:8000/api';
```

**Run the app:**
```bash
flutter run                          # Debug on connected device
flutter build apk --release          # Android release APK
flutter build appbundle --release    # Android Play Store bundle
flutter build ios --release          # iOS (Mac only)
```

**Release APK location:**
```
build/app/outputs/flutter-apk/app-release.apk
```

---

### 6. n8n Automation

1. Access n8n at **http://localhost:5678**
2. Login with `admin` / `{N8N_PASSWORD from .env}`
3. Follow [`automation/N8N_PERMANENT_SETUP.md`](automation/N8N_PERMANENT_SETUP.md) to link your Firebase credentials permanently (eliminates hourly token refresh)

Workflows in `automation/n8n_workflows/` are auto-loaded by Docker.

---

## 📡 API Reference

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/api/auth/register` | — | Register a new user |
| `POST` | `/api/auth/token` | — | Login (returns JWT) |
| `GET` | `/api/auth/me` | ✅ | Get current user profile |
| `POST` | `/api/detections/report` | ✅ | Submit a new fire detection |
| `GET` | `/api/detections/` | — | List detections (with filters) |
| `GET` | `/api/detections/active` | — | Live active fire detections |
| `GET` | `/api/detections/{id}` | — | Get a specific detection |
| `PUT` | `/api/detections/{id}` | ✅ | Update detection status |
| `GET` | `/api/detections/{id}/nearby-stations` | — | Nearest fire stations |
| `GET` | `/api/notifications/` | ✅ | Get notifications for user |
| `POST` | `/api/notifications/{id}/read` | ✅ | Mark notification as read |
| `GET` | `/api/health` | — | API health check |

Full interactive docs available at `/api/docs` when server is running.

---

## ⚙️ Configuration

### Severity Levels

Fire detections are automatically classified based on AI confidence score:

| Severity | Confidence | Color |
|----------|------------|-------|
| 🟤 Low | < 50% | Green |
| 🟡 Medium | 50–70% | Orange |
| 🔴 High | 70–90% | Red |
| ⚫ Critical | > 90% | Dark Red |

### Firebase Security Rules

- **Detections**: Public read, auth-required write, no delete
- **Users**: Auth-required, own-document only
- **Notifications**: Auth-required read, **admin-only write** (backend Admin SDK)
- **Storage**: Images validated by MIME type (`image/*`) and max 10MB size

---

## 🔍 Troubleshooting

| Problem | Solution |
|---------|----------|
| Firebase init fails | Check `firebase-credentials.json` path in `.env` |
| Images fail to upload | Verify `SUPABASE_URL`, `SUPABASE_ANON_KEY` in `.env` |
| SMS not sending | Check Twilio trial account limits and verified numbers |
| Flutter model not loading | Ensure `.tflite` file is in `assets/models/` and declared in `pubspec.yaml` |
| n8n workflows not appearing | Rename folder to match `n8n_workflows` (with underscore) |
| Docker frontend build fails | Ensure directory is `frontend_website` (underscore, not hyphen) |
| Dark mode flash on page load | Inline theme script is already applied in `<head>` of `index.html` |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m "Add your feature"`
4. Push to the branch: `git push origin feature/your-feature`
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License.

---

## 💬 Support

- 📧 Email: vinaykumarbharwal@gmail.com
- 🐛 Issues: [GitHub Issues](https://github.com/vinaykumarbharwal/Project_Fire/issues)

---

*Built with ❤️ for wildfire prevention and public safety.*