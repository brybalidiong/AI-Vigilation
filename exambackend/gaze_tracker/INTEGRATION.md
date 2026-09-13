# Gaze tracker — integration into your invigilator app

Copy **only** the `gaze_tracker` folder into your project (not the whole `TrainModel` folder).

## What to copy

```
your-invigilator-project/
  gaze_tracker/
    __init__.py
    tracker.py
    inference.py
    requirements.txt
    assets/
      EfficientNetB0_gaze_float32.tflite
      class_names.json
      face_landmarker.task    # optional; downloads on first run if missing
```

## Install dependencies

```bash
pip install -r gaze_tracker/requirements.txt
```

## Usage (Python backend)

```python
import cv2
from gaze_tracker import GazeTracker

tracker = GazeTracker()  # loads models from gaze_tracker/assets/
if not tracker.ready:
    raise RuntimeError(tracker.error)

cap = cv2.VideoCapture(0)
ok, frame = cap.read()
result = tracker.analyze(frame)

print(result.label)          # e.g. "Looking at the screen (Normal)"
print(result.confidence)     # 0.0 - 1.0
print(result.is_normal)      # True if looking at screen
print(result.is_suspicious)  # True if not normal or no face
print(result.to_dict())      # JSON-friendly for API responses
```

## Flask example (exam session endpoint)

```python
from flask import Blueprint, jsonify, request
import numpy as np
import cv2
from gaze_tracker import GazeTracker

gaze_bp = Blueprint("gaze", __name__)
_tracker = GazeTracker()

@gaze_bp.route("/api/exam/gaze", methods=["POST"])
def analyze_gaze_frame():
    file = request.files.get("frame")
    if not file:
        return jsonify({"error": "missing frame"}), 400
    arr = np.frombuffer(file.read(), np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    return jsonify(_tracker.analyze(frame).to_dict())
```

Register the blueprint on your main Flask app.

## Custom asset path

```python
tracker = GazeTracker(assets_dir="/path/to/models")
```

## Behaviour (already configured)

- EfficientNetB0 image preprocessing (matches the exported model)
- Browser frames are analyzed in their original camera orientation; mirror the preview with CSS only
- **Normal** when gaze is centered or when top class confidence is **below 80%**
- `no_face` / `gaze_model_unavailable` labels for edge cases

## Do not copy from TrainModel

Training scripts, `app.py` demo, `test_*.py`, `.keras` checkpoints, datasets — not needed at runtime.

## Next step

Open your invigilator project in Cursor and tell the agent where it lives (path or repo). Point it at this `gaze_tracker` folder so it can wire `GazeTracker` into your existing exam flow (WebSocket, periodic snapshots, violation logging, etc.).
