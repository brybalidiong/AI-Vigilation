"""Drop-in gaze detection for an online invigilator backend."""
from __future__ import annotations

import json
import os
import threading
import urllib.request
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

import cv2
import mediapipe as mp
import numpy as np
import tensorflow as tf
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

# pyrefly: ignore [missing-import]
from .inference import (
    ABOVE_VIOLATION_CONFIDENCE_THRESHOLD,
    BELOW_CONFIDENCE_THRESHOLD,
    LEFT_CONFIDENCE_THRESHOLD,
    RIGHT_CONFIDENCE_THRESHOLD,
    VIOLATION_CONFIDENCE_THRESHOLD,
    extract_geometric_features,
    mirror_correct_geo,
    pick_gaze_label,
    prepare_image_batch,
    unmirror_face_crop,
)

_PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_ASSETS = os.path.join(_PACKAGE_DIR, "assets")
_LANDMARKER_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "face_landmarker/face_landmarker/float16/1/face_landmarker.task"
)


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Temporal smoothing
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class _TemporalSmoother:
    """
    Rolling weighted average of per-class probability vectors.
    Newer frames receive linearly higher weights, so the model reacts
    quickly to genuine direction changes but ignores single-frame noise.
    """

    def __init__(self, window: int = 7):
        self._window = window
        self._ramp = np.arange(1, window + 1, dtype=np.float32)
        self._buf: deque[np.ndarray] = deque(maxlen=window)

    def update(self, probs: np.ndarray) -> np.ndarray:
        self._buf.append(probs.astype(np.float32))
        n = len(self._buf)
        stacked = np.stack(list(self._buf), axis=0)  # (n, C)
        w = self._ramp[-n:]
        return (stacked * w[:, None]).sum(0) / w.sum()

    def reset(self) -> None:
        self._buf.clear()


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Hysteresis filter
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class _HysteresisFilter:
    """
    Prevents rapid Normal â†” Violation oscillation.
    Once a violation is flagged, requires `exit_frames` consecutive
    high-confidence Normal predictions before reverting.
    """

    def __init__(
        self,
        normal_idx: int,
        exit_threshold: float = 0.40,
        exit_frames: int = 1,
    ):
        self._normal_idx = normal_idx
        self._exit_threshold = exit_threshold
        self._exit_frames = exit_frames
        self._current_violation: Optional[tuple[int, float]] = None
        self._normal_streak = 0

    def update(self, class_idx: int, confidence: float) -> tuple[int, float]:
        is_normal = class_idx == self._normal_idx

        if self._current_violation is None:
            if not is_normal:
                self._current_violation = (class_idx, confidence)
                self._normal_streak = 0
            return class_idx, confidence
        else:
            if is_normal and confidence >= self._exit_threshold:
                self._normal_streak += 1
                if self._normal_streak >= self._exit_frames:
                    self._current_violation = None
                    self._normal_streak = 0
                    return class_idx, confidence
                return self._current_violation
            else:
                self._normal_streak = 0
                if not is_normal:
                    self._current_violation = (class_idx, confidence)
                return self._current_violation if self._current_violation else (class_idx, confidence)

    def reset(self) -> None:
        self._current_violation = None
        self._normal_streak = 0


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Result dataclass
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@dataclass
class GazeResult:
    """Result of one frame analysis."""

    label: str
    confidence: float
    face_detected: bool
    is_normal: bool
    is_suspicious: bool
    probabilities: dict[str, float] = field(default_factory=dict)
    # Normalised face bounding box [x1, y1, x2, y2] in 0â€“1 range
    # relative to the original (possibly mirrored) frame dimensions.
    # None when no face is detected.
    face_bbox: Optional[list[float]] = None

    def to_dict(self) -> dict:
        d = {
            "label": self.label,
            "confidence": self.confidence,
            "face_detected": self.face_detected,
            "is_normal": self.is_normal,
            "is_suspicious": self.is_suspicious,
            "probabilities": self.probabilities,
        }
        if self.face_bbox is not None:
            d["face_bbox"] = self.face_bbox   # [x1, y1, x2, y2] normalised
        return d


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# GazeTracker
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class GazeTracker:
    """
    Loads gaze TFLite + MediaPipe once; call analyze() per webcam frame.

    Parameters
    ----------
    assets_dir       : folder with gaze_model_float32.tflite, class_names.json,
                       face_landmarker.task (auto-downloaded if missing).
    mirror_webcam    : True if the frame is already mirrored (typical browser webcam).
    smoothing_window : frames to average over for temporal smoothing (0 = off).
    use_hysteresis   : whether to apply exit-frame filter.
    """

    def __init__(
        self,
        assets_dir: Optional[str] = None,
        mirror_webcam: bool = False,
        smoothing_window: int = 0,
        use_hysteresis: bool = False,
    ):
        self.assets_dir = assets_dir or _DEFAULT_ASSETS
        self.mirror_webcam = mirror_webcam
        self._ready = False
        self._error: Optional[str] = None
        self._lock = threading.Lock()

        class_path = os.path.join(self.assets_dir, "class_names.json")
        tflite_path = os.path.join(self.assets_dir, "EfficientNetB0_gaze_float32.tflite")
        landmarker_path = os.path.join(self.assets_dir, "face_landmarker.task")

        if not os.path.isfile(class_path):
            self._error = f"Missing {class_path}"
            return
        if not os.path.isfile(tflite_path):
            self._error = f"Missing {tflite_path}"
            return

        with open(class_path, "r", encoding="utf-8") as f:
            self.classes: list[str] = json.load(f)

        if not os.path.isfile(landmarker_path):
            os.makedirs(self.assets_dir, exist_ok=True)
            urllib.request.urlretrieve(_LANDMARKER_URL, landmarker_path)

        base_options = mp_python.BaseOptions(model_asset_path=landmarker_path)
        options = mp_vision.FaceLandmarkerOptions(
            base_options=base_options,
            running_mode=mp_vision.RunningMode.IMAGE,
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=False,
            num_faces=2,
        )
        self._landmarker = mp_vision.FaceLandmarker.create_from_options(options)

        self._interpreter = tf.lite.Interpreter(model_path=tflite_path)
        self._interpreter.allocate_tensors()
        inputs = self._interpreter.get_input_details()
        outputs = self._interpreter.get_output_details()

        # Resolve tensor indices by name, fall back to position
        img_inputs = [i for i in inputs if "image" in i["name"]]
        geo_inputs = [i for i in inputs if "geo" in i["name"]]
        self._img_idx = img_inputs[0]["index"] if img_inputs else inputs[0]["index"]
        self._geo_idx = geo_inputs[0]["index"] if geo_inputs else (inputs[1]["index"] if len(inputs) > 1 else None)
        self._has_geo_input = self._geo_idx is not None
        self._out_idx = outputs[0]["index"]

        # Read model's expected image dimensions from tensor shape (1, H, W, C)
        img_detail = next(d for d in inputs if d["index"] == self._img_idx)
        self._model_h = int(img_detail["shape"][1])
        self._model_w = int(img_detail["shape"][2])

        self._ready = True

        # Temporal smoothing
        self._smoother = _TemporalSmoother(window=smoothing_window) if smoothing_window > 1 else None

        # Hysteresis
        normal_idx = next(
            (i for i, n in enumerate(self.classes) if "normal" in n.lower()), 3
        )
        self._hysteresis = _HysteresisFilter(normal_idx=normal_idx) if use_hysteresis else None

    @property
    def ready(self) -> bool:
        return self._ready

    @property
    def error(self) -> Optional[str]:
        return self._error

    def reset_temporal_state(self) -> None:
        """Call at the start of each new exam attempt to flush rolling buffers."""
        if self._smoother:
            self._smoother.reset()
        if self._hysteresis:
            self._hysteresis.reset()

    def _crop_face(self, frame: np.ndarray, result) -> tuple[np.ndarray | None, tuple | None]:
        if not result.face_landmarks:
            return None, None

        h, w = frame.shape[:2]
        lm = result.face_landmarks[0]
        xs = [l.x * w for l in lm]
        ys = [l.y * h for l in lm]

        xmin, xmax = int(min(xs)), int(max(xs))
        ymin, ymax = int(min(ys)), int(max(ys))
        box_w, box_h = xmax - xmin, ymax - ymin

        # 25% padding gives more context for gaze direction inference
        padding_x = int(box_w * 0.25)
        padding_y = int(box_h * 0.25)

        x1 = max(0, xmin - padding_x)
        y1 = max(0, ymin - padding_y)
        x2 = min(w, xmax + padding_x)
        y2 = min(h, ymax + padding_y)

        face_crop = frame[y1:y2, x1:x2]
        if face_crop.size == 0:
            return None, None

        # Resize to model's actual expected resolution
        resized = cv2.resize(
            face_crop,
            (self._model_w, self._model_h),
            interpolation=cv2.INTER_LANCZOS4,
        )
        # Return tight bbox (without padding) as absolute pixel coords [x1,y1,x2,y2]
        tight_x1 = max(0, xmin)
        tight_y1 = max(0, ymin)
        tight_x2 = min(w, xmax)
        tight_y2 = min(h, ymax)
        return resized, (tight_x1, tight_y1, tight_x2, tight_y2)

    def analyze(self, frame_bgr: np.ndarray) -> GazeResult:
        """
        Analyze one OpenCV BGR frame (e.g. decoded from a browser WebRTC frame).
        Returns GazeResult; non-ready or no-face conditions return descriptive labels.
        """
        with self._lock:
            if not self._ready:
                return GazeResult(
                    label="gaze_model_unavailable",
                    confidence=0.0,
                    face_detected=False,
                    is_normal=False,
                    is_suspicious=False,
                )

            if frame_bgr is None or frame_bgr.size == 0:
                return GazeResult(
                    label="no_frame",
                    confidence=0.0,
                    face_detected=False,
                    is_normal=False,
                    is_suspicious=False,
                )

            frame = cv2.flip(frame_bgr, 1) if getattr(self, 'mirror_webcam', False) else frame_bgr.copy()
            h, w = frame.shape[:2]

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            
            results = self._landmarker.detect(mp_image)

            if not results.face_landmarks:
                if getattr(self, '_smoother', None):
                    self._smoother.reset()
                if getattr(self, '_hysteresis', None):
                    self._hysteresis.reset()
                return GazeResult(
                    label="no_face",
                    confidence=1.0,
                    face_detected=False,
                    is_normal=False,
                    is_suspicious=True,
                )

            if len(results.face_landmarks) > 1:
                if getattr(self, '_smoother', None):
                    self._smoother.reset()
                if getattr(self, '_hysteresis', None):
                    self._hysteresis.reset()
                return GazeResult(
                    label="multiple_people",
                    confidence=1.0,
                    face_detected=True,
                    is_normal=False,
                    is_suspicious=True,
                    probabilities={},
                )

            processed_face, _bbox = self._crop_face(frame, results)
            if processed_face is None:
                return GazeResult(
                    label="no_face",
                    confidence=1.0,
                    face_detected=False,
                    is_normal=False,
                    is_suspicious=True,
                )

            model_face = unmirror_face_crop(processed_face) if getattr(self, 'mirror_webcam', False) else processed_face
            batched_face = prepare_image_batch(model_face)
            geo = mirror_correct_geo(extract_geometric_features(results, h, w))
            geo_batch = np.expand_dims(geo, axis=0).astype(np.float32)

            self._interpreter.set_tensor(self._img_idx, batched_face)
            if self._has_geo_input:
                self._interpreter.set_tensor(self._geo_idx, geo_batch)

            self._interpreter.invoke()
            raw_predictions = self._interpreter.get_tensor(self._out_idx)[0]

        # ── Temporal smoothing ────────────────────────────────────────────
        predictions = self._smoother.update(raw_predictions) if getattr(self, '_smoother', None) else raw_predictions

        # ── Label selection ───────────────────────────────────────────────
        class_idx, confidence = pick_gaze_label(predictions, geo, self.classes)

        # ── Hysteresis filter ─────────────────────────────────────────────
        if getattr(self, '_hysteresis', None):
            class_idx, confidence = self._hysteresis.update(class_idx, confidence)

        label = self.classes[class_idx]
        is_normal = "normal" in label.lower()

        label_l = label.lower()
        if is_normal:
            is_suspicious = False
        elif "left" in label_l and "right" not in label_l:
            is_suspicious = confidence >= LEFT_CONFIDENCE_THRESHOLD
        elif "right" in label_l and "left" not in label_l:
            is_suspicious = confidence >= RIGHT_CONFIDENCE_THRESHOLD
        elif "above" in label_l:
            is_suspicious = confidence >= ABOVE_VIOLATION_CONFIDENCE_THRESHOLD
        elif "below" in label_l:
            is_suspicious = confidence >= BELOW_CONFIDENCE_THRESHOLD
        else:
            is_suspicious = confidence >= VIOLATION_CONFIDENCE_THRESHOLD

        probs = {self.classes[i]: float(raw_predictions[i]) for i in range(len(self.classes))}

        # Normalize bbox back to [0,1] relative to the (possibly mirrored) frame size
        norm_bbox = None
        if _bbox is not None:
            x1n, y1n, x2n, y2n = _bbox
            norm_bbox = [
                round(x1n / w, 4),
                round(y1n / h, 4),
                round(x2n / w, 4),
                round(y2n / h, 4),
            ]

        return GazeResult(
            label=label,
            confidence=confidence,
            face_detected=True,
            is_normal=is_normal,
            is_suspicious=is_suspicious,
            probabilities=probs,
            face_bbox=norm_bbox,
        )
