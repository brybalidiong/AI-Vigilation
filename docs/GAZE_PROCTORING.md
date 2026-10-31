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

### Switching the gaze classifier

The admin Gaze model page stores one selection for the entire backend. EfficientNet
is the recommended default. MobileNetV2 and ResNet50 appear as unavailable until
their runtime exports are placed beside the current model in `GAZE_ASSETS_DIR`
(`exambackend/gaze_tracker/assets/` locally and on the Azure host). The selection
is shared through the database and each worker refreshes it within two seconds.
Changing models does not change face detection, iris visibility, gaze direction
rules, warnings, evidence, or strike thresholds. Test and calibrate each new
model before using it in a real exam.

Required runtime files:

| Model | TFLite filename |
| --- | --- |
| Existing EfficientNet | `EfficientNetB0_gaze_float32.tflite` |
| MobileNetV2 | `MobileNetV2_gaze_float32.tflite` |
| ResNet50 | `ResNet50_gaze_float32.tflite` |

The three models share the existing `class_names.json` and
`face_landmarker.task`; do not replace the five labels or change their order.
Each TFLite model must accept one float32 RGB image tensor of shape
`[1, height, width, 3]` containing raw pixel values in `[0, 255]`. Include any
MobileNetV2 or ResNet50 normalization *inside the exported model*. An optional
second float32 geometry input must be `[1, 14]`. The sole output must be
`[1, 5]` float32 softmax probabilities in the shared label order: above, left,
right, normal, below. The admin endpoint validates these requirements and refuses
to switch to a missing or incompatible export. Training datasets, `.keras` or
`.h5` checkpoints, and notebooks are not runtime inputs.

The backend reads the model files from its host-mounted, Git-ignored assets
folder. Copy the new `.tflite` files to that folder on every deployed backend
host; Vercel does not host or run these models. Keep the existing EfficientNet
file for a reliable fallback.

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
The next frame is captured on the next browser event-loop turn after the previous
result arrives, so a slow inference
cannot create a browser queue of stale frames. The backend keeps one active
gaze inference and at most one waiting frame; when busy, it asks the browser to retry with
a fresh image after 100 ms. A one-second HTTP observer remains available for
strike counting when the WebSocket is unavailable. The browser sends unmirrored pixels;
the CSS selfie preview does not change the left/right direction used by inference.
If a WebSocket result is too old to affect gaze state, the browser discards it and
sends a fresh frame on the same connection. A missing response still closes the
socket and activates the HTTP fallback. When the exam shows "Reconnecting," check
the browser's `[GazeWS] closed` console entry for its close code and cause, then
check backend errors and model availability; the label alone does not identify
a student network problem.
Gaze sockets use a local Channels layer because they do not join groups or
receive cross-process messages. This keeps Redis read timeouts from closing
the live gaze stream; exam-publishing updates continue to use Redis. After
startup, the browser allows 12 seconds for a gaze reply before reconnecting.
Results older than 2.5 seconds are discarded so they cannot create delayed strikes.
Before each exam, the camera precheck posts webcam frames to the authenticated
`/api/student/exams/<exam_id>/precheck-face/` endpoint. YuNet returns a
normalized face box without starting an exam attempt or storing the frame.
Continue stays disabled until two consecutive frames show one face at least 16% of
the frame width and 22% of its height. A smaller or undetected face prompts the
student to move closer; multiple faces or unavailable inference also block entry.
The precheck warns that excessive distance can cause no-face violations during
the exam. Face identity verification still follows the precheck.
Raw head yaw keeps its trained-model feature value; direction selection converts
its camera sign to the student's left/right perspective. Eye position takes
priority when a clear eye movement and head turn disagree. Iris X is converted
from camera coordinates before it is blended with yaw. The browser sends a 640-pixel-wide
gaze JPEG at 0.75 quality to retain iris detail. Strong horizontal geometry
can correct a mirrored left/right or normal prediction. When Normal leads and
below has only weak model support, a clear side turn takes precedence over a
modest downward iris shift. A clear up/down model prediction remains. A first
confident left/right frame appears in the camera direction indicator while a
second frame confirms it for strike
timing. Up/down appears on the first valid result. Strong vertical eye geometry
can select up/down even when Normal has the highest model probability, provided
the model supports that direction. An above override also needs a clear upward
iris shift in both eyes, or upward iris and head-pitch agreement, to avoid
normal-eye jitter and a noisy single iris landmark. A model-only above
prediction also needs upward eye evidence or a clear upward head tilt.
When clear sideways geometry conflicts with above and the eyes do not point
upward, the sideways direction takes precedence.
The below confidence gate is 0.25; the
above gate is 0.22. The continuous look-away strike window remains four seconds.

Brief look-away detections above 90% confidence also enter one shared tally
across left, right, above, and below. A sustained direction counts once per
episode; two neutral frames rearm the same direction, while a different
direction begins a new episode. The configured exam time limit sets the shared
threshold: 5 detections below 30 minutes, 10 detections from 30 minutes to under
2 hours, and 15 detections for 2 hours or longer. An unlimited exam (time limit
0) also uses 15. At the threshold, the server records one `gaze_violation`
event and resets the brief-gaze tally. This uses the same
eight-violation termination limit as the existing four-second look-away rule.
The browser sends the exact signed WebSocket frame when an episode begins;
HTTP fallback counts episodes on its own. Duplicate uploads of one frame are
ignored. The warning names the general gaze violation rather than a specific
direction. No-face violations remain a separate counter.

### Iris visibility during the exam

The tracker also compares actual eye pixels around MediaPipe iris landmarks. A
landmark by itself is not proof that the iris can be seen through tinted lenses.
One open eye with a discernible iris and surrounding sclera is sufficient, so a
reflection on one prescription lens does not block the student. Gaze direction
selection and strike thresholds are independent of this check.

The browser covers the exam controls until a recent clear-eye frame arrives and
shows guidance to remove dark glasses or adjust prescription lenses and lighting.
The HTTP gaze observation records the last clear-eye time on the active attempt;
the advance and submit endpoints require that confirmation within ten seconds.
An expired exam timer can still submit answers automatically. The exam clock does
not pause. Pixel visibility is a practical check, not a definitive sunglasses
classifier, and very poor lighting or heavy reflections may require adjustment.

Gadget checks reuse a capture canvas and send a 640-pixel-wide JPEG at 0.7
quality. A new frame is captured on the next event-loop turn after a clear
response, or 100 ms while a device remains visible. Starting, disabled, and
busy checks retry after 150 ms;
unavailable checks retry after 500 ms. Only one browser request is in flight.
The backend runs at most one inference and queues one additional frame; excess
frames receive a quick busy response so stale frames cannot build up. Responses
from an ended exam loop cannot update the next exam's warning state. The camera
preview shows scanner status and warning counts without gadget bounding boxes.
The production ASGI worker warms both models in the background at startup so
the first student's exam does not trigger a cold model load. The dashboard
warmup endpoint remains a fallback when a worker is still starting.
Production also uses a four-connection psycopg pool so repeated ASGI requests
reuse Supabase connections without keeping a Django connection pinned to each
request. SQLite tests do not use the pool.
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
