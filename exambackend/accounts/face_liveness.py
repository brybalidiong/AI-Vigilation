"""Short blink challenge for exam identity checks, independent of gaze proctoring."""

import os
import threading
from pathlib import Path

import cv2
import numpy as np


_LEFT_EYE = (33, 160, 158, 133, 153, 144)
_RIGHT_EYE = (362, 385, 387, 263, 373, 380)
_model = None
_model_lock = threading.Lock()
_detect_lock = threading.Lock()


def _landmarker_path():
    backend = Path(__file__).resolve().parent.parent
    candidates = [
        Path(os.environ['GAZE_ASSETS_DIR']) if os.environ.get('GAZE_ASSETS_DIR') else None,
        backend / 'gaze_tracker' / 'assets',
        backend.parent / 'TrainModel' / 'gaze_tracker' / 'assets',
    ]
    for directory in candidates:
        if directory and (directory / 'face_landmarker.task').is_file():
            return str(directory / 'face_landmarker.task')
    raise RuntimeError('Face liveness model unavailable.')


def _get_landmarker():
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                import mediapipe as mp
                from mediapipe.tasks import python as mp_python
                from mediapipe.tasks.python import vision

                options = vision.FaceLandmarkerOptions(
                    base_options=mp_python.BaseOptions(model_asset_path=_landmarker_path()),
                    running_mode=vision.RunningMode.IMAGE,
                    num_faces=2,
                )
                _model = (mp, vision.FaceLandmarker.create_from_options(options))
    return _model


def eye_aspect_ratio(landmarks, indices, width, height):
    """Normalized eyelid opening, unaffected by the face's size in the frame."""
    points = [np.array((landmarks[index].x * width, landmarks[index].y * height), dtype=np.float32) for index in indices]
    width = np.linalg.norm(points[0] - points[3])
    if width < 0.005:
        return 0.0
    return float((np.linalg.norm(points[1] - points[5]) + np.linalg.norm(points[2] - points[4])) / (2 * width))


def _reopened_frame_index(ratios):
    """Find the first open frame after both eyes close."""
    if len(ratios) < 8 or any(pair is None for pair in ratios[:3]):
        return None
    baseline = float(np.median([min(pair) for pair in ratios[:3]]))
    if baseline < 0.18:
        return None
    closed_limit = min(0.15, baseline * 0.65)
    open_limit = max(0.17, baseline * 0.78)
    closed_at = None
    for index, pair in enumerate(ratios[3:], start=3):
        if pair is None:
            return None
        left, right = pair
        if closed_at is None and left < closed_limit and right < closed_limit:
            closed_at = index
        elif closed_at is not None and index > closed_at and left >= open_limit and right >= open_limit:
            return index
    return None


def blink_sequence_detected(ratios):
    return _reopened_frame_index(ratios) is not None


def check_blink_frames(frame_bytes):
    """Return a suitable open-eye frame for identity matching after a real blink."""
    mp, landmarker = _get_landmarker()
    ratios = []
    for raw in frame_bytes:
        frame = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            return None
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        with _detect_lock:
            result = landmarker.detect(image)
        if len(result.face_landmarks) != 1:
            return None
        landmarks = result.face_landmarks[0]
        height, width = frame.shape[:2]
        ratios.append((
            eye_aspect_ratio(landmarks, _LEFT_EYE, width, height),
            eye_aspect_ratio(landmarks, _RIGHT_EYE, width, height),
        ))
    reopened_at = _reopened_frame_index(ratios)
    return frame_bytes[reopened_at] if reopened_at is not None else None
