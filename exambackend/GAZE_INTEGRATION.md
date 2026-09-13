# Gaze AI (TrainModel) integration

The **TrainModel** folder at the repo root holds training scripts; **runtime** uses `exambackend/gaze_tracker/`.

## One-time setup

```powershell
cd exambackend
..\.venv\Scripts\pip install -r requirements.txt
..\.venv\Scripts\python scripts\sync_gaze_assets.py
..\.venv\Scripts\python manage.py migrate
```

Verify model loads:

```powershell
..\.venv\Scripts\python manage.py shell -c "from accounts.gaze_service import gaze_tracker_status; print(gaze_tracker_status())"
```

Staff API: `GET /api/gaze/status/` (JWT, staff user).

## During student exam

- Webcam required; frames sent every **5s** to `POST /api/student/exams/<id>/proctoring/gaze/`
- Strikes logged: `gaze_violation`, `gaze_no_face`
- Auto-terminate at **8** look-away / **5** face-not-visible strikes
- Violations save **screenshot evidence** linked to the event

## Instructor reports

- **Exam Progress** → **View report**: gaze counts, action log, screenshots
- Integrity score includes gaze penalties

## Asset paths (first match wins)

1. `GAZE_ASSETS_DIR` environment variable  
2. `exambackend/gaze_tracker/assets/`  
3. `TrainModel/gaze_tracker/assets/`

After updating models in TrainModel, run `scripts/sync_gaze_assets.py` again.
