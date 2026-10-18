# AI-Vigilation — Online Exam Invigilator System

> A capstone project: an AI-powered online exam proctoring platform that monitors student integrity in real time using gaze tracking, face verification, and behavioral analysis.

---

## Features

- 🎓 **Role-based dashboards** — Student, Instructor, and Admin portals
- 👁️ **AI Gaze Tracking** — Real-time eye-gaze proctoring using a TFLite model + MediaPipe face landmarks
- 🤳 **Face Verification** — Student identity verified with OpenCV face models before exams
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
| Daphne + Django Channels | WebSocket server for live proctoring and exam updates |
| PostgreSQL (Supabase) | Primary database |
| Firebase Admin SDK | Authentication & push notifications |
| MediaPipe + TensorFlow Lite | Gaze direction inference |
| OpenCV | Frame capture & face cropping |
| OpenCV YuNet + SFace | Face enrollment & verification |
| Gunicorn | HTTP serving when WebSocket updates are handled by an ASGI server |

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
│   │   ├── face_service.py   # OpenCV face verification
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

For production setup with Vercel, an Azure for Students VM, and the existing Supabase
project, see the [Deployment guide](docs/DEPLOYMENT.md). The frontend is a
Vercel project rooted at `examfrontend/`; the backend uses the Compose setup
in `exambackend/`. Test proctoring with the expected number of simultaneous
students before a live exam.

### Prerequisites
- Python 3.12+
- Node.js 20.19+ or 22.12+
- PostgreSQL (or a Supabase project)
- Firebase project
- Firebase Admin service-account credentials
- Local face and gaze model assets

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
# Set Firebase credentials and any local database settings in .env

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

Use [exambackend/.env.example](exambackend/.env.example) for local configuration.
See the [deployment guide](docs/DEPLOYMENT.md) for production secrets and
hosting settings.

### `examfrontend/.env`
```
VITE_BACKEND_URL=http://localhost:8000
VITE_FIREBASE_API_KEY=...
VITE_FIREBASE_AUTH_DOMAIN=...
VITE_FIREBASE_PROJECT_ID=...
```

---

When an instructor publishes an exam, connected students in that course receive a
WebSocket update and their dashboard reloads its exam list. Uploading creates a
draft; students only see published exams assigned to their section. A single
backend process can use the default in-memory channel layer for local development.
Set `REDIS_URL` and run an ASGI server such as Daphne when deploying multiple
backend processes so updates reach every connected student.

---

## Gaze Model Assets

Some AI model files are excluded from the repository due to file size.
If gaze assets are missing after cloning, copy them into
`exambackend/gaze_tracker/assets/`:

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
