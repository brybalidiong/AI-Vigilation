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
WebSocket. The camera precheck uses an authenticated HTTP request, while the
exam gaze stream sends a student JWT through its WebSocket; both require an
active, enrolled student assigned to a published exam.
The next frame is sent after the previous result arrives, so a slow inference
cannot create a queue of stale frames. A one-second HTTP observer remains available for
strike counting when the WebSocket is unavailable. The browser sends unmirrored pixels;
the CSS selfie preview does not change the left/right direction used by inference.
If a WebSocket result is too old to affect gaze state, the browser discards it and
sends a fresh frame on the same connection. A missing response still closes the
socket and activates the HTTP fallback. When the exam shows "Reconnecting," check
the browser's `[GazeWS] closed` console entry for its close code and cause, then
check backend errors and model availability; the label alone does not identify
a student network problem.
Before each exam, the camera precheck posts webcam frames to the authenticated
`/api/student/exams/<exam_id>/precheck-face/` endpoint. YuNet returns a
normalized face box without starting an exam attempt or storing the frame.
Continue stays disabled until two consecutive frames show one face at least 16% of
the frame width and 22% of its height. A smaller or undetected face prompts the
student to move closer; multiple faces or unavailable inference also block entry.
The precheck warns that excessive distance can cause no-face violations during
the exam. Face identity verification still follows the precheck.
Head yaw keeps the student's left/right sign; iris X is converted from camera
coordinates before the two are blended. The browser sends a 640-pixel-wide
gaze JPEG at 0.75 quality to retain iris detail. Strong horizontal geometry
can correct a mirrored left/right or normal prediction, but does not replace
a clear up/down model prediction.

Gadget checks send a 640-pixel-wide JPEG 40 ms after each active response;
starting, disabled, and unavailable checks retry every 150 ms. A new frame is
captured only after the prior request finishes, and responses from an ended
exam loop cannot update the next exam's warning state.
The camera requests 1280-by-960 capture where supported. The backend uses YOLO at
640 pixels with a 0.25 default confidence threshold;
`GADGET_IMGSZ` and `GADGET_CONFIDENCE` can override these defaults. Checks stay
sequential so slow inference cannot build a backlog of old frames. A failed model
warmup returns an error instead of leaving the scanner in a permanent warming state;
the exam camera shows whether gadget scanning is starting, active, or unavailable.
The live instructor snapshot replaces the prior stored snapshot for that attempt;
separate integrity evidence remains in its own records.

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
