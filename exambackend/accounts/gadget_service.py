"""Lazy, isolated YOLO detection for prohibited exam devices."""
from __future__ import annotations

import os
import threading
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np


# Two workers so a still-running synthetic warmup predict cannot starve real
# exam frames. All YOLO predict() calls are serialized via _infer_lock.
GADGET_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix='gadget-inference')
_warmup_lock = threading.Lock()
_infer_lock = threading.Lock()
_warmup_future = None

DEFAULT_GADGET_NAMES = {'cell phone', 'laptop'}
# COCO class ids: laptop=63, cell phone=67 — limits NMS work to gadget classes.
_GADGET_CLASS_IDS = (63, 67)
# Small phones disappear when a webcam frame is reduced to 320 pixels.
_GADGET_IMGSZ = int(os.getenv('GADGET_IMGSZ', '640'))


@lru_cache(maxsize=1)
def get_gadget_detector():
    from ultralytics import YOLO

    bundled_model = Path(__file__).resolve().parent.parent / 'models' / 'yolo11n.pt'
    model_path = os.getenv(
        'GADGET_MODEL_PATH',
        str(bundled_model) if bundled_model.is_file() else 'yolo11n.pt',
    )
    return YOLO(model_path)


def warm_gadget_detector() -> bool:
    """Load/download the detector in its own worker without blocking a request."""
    global _warmup_future
    if gadget_detector_ready() or gadget_detector_error():
        return False
    with _warmup_lock:
        if gadget_detector_ready() or gadget_detector_error():
            return False
        if _warmup_future and not _warmup_future.done():
            return False
        def initialize():
            detector = get_gadget_detector()
            # Run one synthetic frame so PyTorch graph/setup cost is paid before
            # the student enters an exam, not on their first monitored frame.
            with _infer_lock:
                detector.predict(
                    source=np.zeros((480, 640, 3), dtype=np.uint8),
                    conf=0.25,
                    imgsz=_GADGET_IMGSZ,
                    classes=list(_GADGET_CLASS_IDS),
                    max_det=5,
                    device='cpu',
                    verbose=False,
                )
            return detector

        _warmup_future = GADGET_EXECUTOR.submit(initialize)
        return True


def gadget_detector_ready() -> bool:
    """Only report ready after both model loading and first inference succeed."""
    return bool(get_gadget_detector.cache_info().currsize) and (
        _warmup_future is None or (
            _warmup_future.done() and _warmup_future.exception() is None
        )
    )


def gadget_detector_error():
    """Surface a failed background warmup instead of returning 202 forever."""
    if _warmup_future and _warmup_future.done():
        return _warmup_future.exception()
    return None


def detect_gadgets(raw: bytes) -> list[dict]:
    frame = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError('Invalid image')

    detector = get_gadget_detector()
    confidence = float(os.getenv('GADGET_CONFIDENCE', '0.25'))
    configured = os.getenv('GADGET_CLASSES', '')
    wanted = {
        name.strip().lower()
        for name in configured.split(',')
        if name.strip()
    } or DEFAULT_GADGET_NAMES

    with _infer_lock:
        results = detector.predict(
            source=frame,
            conf=confidence,
            imgsz=_GADGET_IMGSZ,
            classes=list(_GADGET_CLASS_IDS),
            max_det=5,
            device='cpu',
            verbose=False,
        )
    detections = []
    for result in results:
        names = result.names
        for box in result.boxes:
            class_id = int(box.cls[0].item())
            label = str(names[class_id]).lower()
            if label not in wanted:
                continue
            detections.append({
                'label': label,
                'confidence': round(float(box.conf[0].item()), 4),
                'box': [round(float(value), 1) for value in box.xyxy[0].tolist()],
            })
    return detections
