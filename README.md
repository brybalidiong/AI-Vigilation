# AI-Vigilation — Online Exam Invigilator System

> A capstone project: an AI-powered online exam proctoring platform that monitors student integrity in real time using gaze tracking, face verification, and behavioral analysis.

---

## Features

- 🎓 **Role-based dashboards** — Student, Instructor, and Admin portals
- 👁️ **AI Gaze Tracking** — Real-time eye-gaze proctoring using a TFLite model + MediaPipe face landmarks
- 🤳 **Face Verification** — Student identity verified via Microsoft Azure Face API before exams
- 📊 **Integrity Reports** — Automated proctoring event logs and violation summaries per submission
- 📝 **Exam Management** — Create, assign, and time-limit exam sets with multiple question types (MCQ, enumeration, essay)
- 📥 **Aiken Import** — Bulk question import via Aiken-format text files
- 🔴 **Live Proctoring** — WebSocket-based real-time monitoring with snapshot capture
- 🔐 **JWT Authentication** — Secure login with refresh tokens via Firebase
- 📱 **QR / OTP** — Two-factor identity options

---

## Tech Stack

### Backend
| Technology | Purpose |
|---|---|
| Django 6 + DRF | REST API & business logic |
| Daphne + Django Channels | WebSocket server for live proctoring |
| PostgreSQL (Supabase) | Primary database |
| Firebase Admin SDK | Authentication & push notifications |
| MediaPipe + TensorFlow Lite | Gaze direction inference |
| OpenCV | Frame capture & face cropping |
| Azure Face API | Face enrollment & verification |
| Gunicorn | Production WSGI server |

### Frontend
| Technology | Purpose |
|---|---|
| Vue 3 + Vite | SPA framework |
| Vue Router | Client-side routing |
| Axios | HTTP client |
| Firebase JS SDK | Auth token management |

---

## Project Structure

```
AI-Vigilation/
├── exambackend/              # Django backend
│   ├── accounts/             # Core app: models, views, APIs
│   │   ├── models.py         # User, Exam, Submission, Proctoring models
│   │   ├── views.py          # REST API endpoints
│   │   ├── consumers.py      # WebSocket consumers
│   │   ├── gaze_service.py   # Gaze AI singleton service
│   │   ├── face_service.py   # Azure face verification
│   │   └── grading.py        # Auto-grading logic
│   ├── gaze_tracker/         # Gaze AI package
│   │   ├── inference.py      # TFLite model inference
│   │   ├── tracker.py        # GazeTracker class
│   │   └── assets/           # Model files (.tflite, .task)
│   ├── scripts/
│   │   └── sync_gaze_assets.py
│   └── requirements.txt
│
├── examfrontend/             # Vue 3 frontend
│   └── src/
│       ├── views/            # Dashboard pages (Student, Instructor, Admin)
│       ├── components/       # Reusable UI components
│       └── router/           # Route definitions
│
└── docs/                     # ERD and integration docs
```

---

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 20+
- PostgreSQL (or a Supabase project)
- Firebase project
- Azure Face API key

### Backend Setup

```bash
cd exambackend

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Fill in your DB, Firebase, and Azure credentials in .env

# Run migrations
python manage.py migrate

# Start the development server
python manage.py runserver
```

On Windows, if this checkout already has a repository-level `.venv`, start the
backend with that interpreter explicitly from `exambackend/`:

```powershell
& ..\.venv\Scripts\python.exe -c "import ultralytics"
& ..\.venv\Scripts\python.exe manage.py runserver
```

The gadget scanner requires `ultralytics` in the Python environment running
Django. Launching `manage.py` with a different system Python can leave gadget
detection unavailable even when the package is installed in `.venv`.

### Frontend Setup

```bash
cd examfrontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Fill in your Firebase and API URL in .env

# Start the development server
npm run dev
```

---

## Environment Variables

### `exambackend/.env`
```
DATABASE_URL=your_supabase_postgres_url
FIREBASE_CREDENTIALS=path/to/serviceAccountKey.json
AZURE_FACE_API_KEY=your_azure_key
AZURE_FACE_ENDPOINT=your_azure_endpoint
GAZE_ASSETS_DIR=           # optional override for model assets path
```

### `examfrontend/.env`
```
VITE_API_BASE_URL=http://localhost:8000
VITE_FIREBASE_API_KEY=...
VITE_FIREBASE_AUTH_DOMAIN=...
VITE_FIREBASE_PROJECT_ID=...
```

---

## Gaze Model Assets

The AI model files (`.tflite`, `.task`) are excluded from the repository due to file size.
After cloning, copy them into `exambackend/gaze_tracker/assets/`:

```bash
python exambackend/scripts/sync_gaze_assets.py
```

Or set the `GAZE_ASSETS_DIR` environment variable to point to your local assets folder.

---

## User Roles

| Role | Capabilities |
|---|---|
| **Student** | Take exams, view results, manage profile & face enrollment |
| **Instructor** | Create/manage courses, exam sets, questions, view reports |
| **Admin** | Full system access, user management, integrity overview |

---

## License

This project is a capstone submission and is intended for academic purposes.
