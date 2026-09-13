# Gaze AI proctoring (integrated)

## Backend layout

```
exambackend/
  gaze_tracker/          # Copied from TrainModel — do not edit unless retraining
    assets/              # gaze_model_float32.tflite, class_names.json, face_landmarker.task
  accounts/
    gaze_service.py      # Loads GazeTracker once
```

## API

`POST /api/student/exams/<exam_id>/proctoring/gaze/`

- Auth: student JWT (same as other exam routes)
- Body: `multipart/form-data` with field `image` (JPEG webcam frame)
- Response: `{ label, confidence, face_detected, is_normal, is_suspicious, probabilities, logged_event? }`
- Logs `gaze_violation` or `gaze_no_face` proctoring events when applicable

## Setup

```bash
cd exambackend
pip install -r requirements.txt
python manage.py migrate
```

## Frontend

During an exam, `StudentDashboardView.vue` sends a frame every **5 seconds** to the gaze endpoint and shows a warning overlay when the student is not looking at the screen.

## Updating the model

Replace files in `exambackend/gaze_tracker/assets/` and restart the Django server.

## Auto-terminate limits

| Strike type | Limit |
|-------------|-------|
| Look away (`gaze_violation`) | **8** strikes |
| Face not visible (`gaze_no_face`) | **5** strikes |

Checks run every **5 seconds**. When a limit is reached, the gaze API returns `should_terminate: true` and the exam is force-submitted.

## Instructor integrity report

Shows **Gaze away** / **Face hidden** stats, highlights gaze events in the action log, and records termination reason on submit.
