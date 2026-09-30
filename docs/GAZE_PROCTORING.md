# Gaze AI proctoring (integrated)

## Backend layout

```
exambackend/
  gaze_tracker/          # Runtime gaze inference
    assets/              # EfficientNetB0_gaze_float32.tflite, class_names.json, face_landmarker.task
  accounts/
    gaze_service.py      # Loads GazeTracker once
```

## API

`POST /api/student/exams/<exam_id>/proctoring/gaze/`

- Auth: student JWT (same as other exam routes)
- Body: `multipart/form-data` with field `image` (JPEG webcam frame). A WebSocket result can
  include `frame_receipt` so the API reuses the exact frame that was classified.
- Response: `{ label, confidence, face_detected, is_normal, is_suspicious, probabilities, logged_event? }`
- Logs `gaze_violation` or `gaze_no_face` proctoring events when applicable

## Setup

```bash
cd exambackend
pip install -r requirements.txt
python manage.py migrate
```

## Frontend

During an exam, `StudentDashboardView.vue` streams one JPEG at a time over the gaze
WebSocket. The next frame is sent after the previous result arrives, so a slow inference
cannot create a queue of stale frames. A one-second HTTP observer remains available for
strike counting when the WebSocket is unavailable. The browser sends unmirrored pixels;
the CSS selfie preview does not change the left/right direction used by inference.
Head yaw keeps the student's left/right sign; iris X is converted from camera
coordinates before the two are blended. Up/down geometry thresholds allow a
slightly smaller deliberate movement than before.

Gadget checks send a 640-pixel-wide JPEG roughly every 150 ms after each response.
The camera requests 1280-by-960 capture where supported. The backend uses YOLO at
640 pixels with a 0.25 default confidence threshold;
`GADGET_IMGSZ` and `GADGET_CONFIDENCE` can override these defaults. Checks stay
sequential so slow inference cannot build a backlog of old frames. A failed model
warmup returns an error instead of leaving the scanner in a permanent warming state;
the exam camera shows whether gadget scanning is starting, active, or unavailable.

## Updating the model

Replace files in `exambackend/gaze_tracker/assets/` and restart the Django server.

## Auto-terminate limits

| Strike type | Limit |
|-------------|-------|
| Look away (`gaze_violation`) | **8** strikes |
| Face not visible (`gaze_no_face`) | **5** strikes |

When a limit is reached, the gaze API returns `should_terminate: true` and the exam is force-submitted.

## Instructor integrity report

Shows **Gaze away** / **Face hidden** stats, highlights gaze events in the action log, and records termination reason on submit.
