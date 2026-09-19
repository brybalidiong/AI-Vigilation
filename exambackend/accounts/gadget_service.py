"""Lazy, isolated YOLO detection for prohibited exam devices."""
from __future__ import annotations

import os
import threading
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np


GADGET_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix='gadget-inference')
_warmup_lock = threading.Lock()
_warmup_future = None

DEFAULT_GADGET_NAMES = {'cell phone', 'laptop'}


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
    if get_gadget_detector.cache_info().currsize:
        return False
    with _warmup_lock:
        if get_gadget_detector.cache_info().currsize:
            return False
        if _warmup_future and not _warmup_future.done():
            return False
        def initialize():
            detector = get_gadget_detector()
            # Run one synthetic frame so PyTorch graph/setup cost is paid before
            # the student enters an exam, not on their first monitored frame.
            detector.predict(
                source=np.zeros((480, 640, 3), dtype=np.uint8),
                conf=0.55,
                imgsz=640,
                device='cpu',
                verbose=False,
            )
            return detector

        _warmup_future = GADGET_EXECUTOR.submit(initialize)
        return True


def detect_gadgets(raw: bytes) -> list[dict]:
    frame = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError('Invalid image')

    detector = get_gadget_detector()
    confidence = float(os.getenv('GADGET_CONFIDENCE', '0.55'))
    configured = os.getenv('GADGET_CLASSES', '')
    wanted = {
        name.strip().lower()
        for name in configured.split(',')
        if name.strip()
    } or DEFAULT_GADGET_NAMES

    results = detector.predict(
        source=frame,
        conf=confidence,
        imgsz=640,
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
