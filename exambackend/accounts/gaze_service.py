"""Lazy-loaded gaze tracker for exam proctoring."""
from __future__ import annotations

import os
import sys
import threading
import hashlib
import logging
from concurrent.futures import ThreadPoolExecutor
from django.core import signing
from django.db import close_old_connections
from collections import deque
from functools import lru_cache
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)
# Inference must never queue behind database queries or remote image uploads.
GAZE_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix='gaze-inference')
_inference_slots = threading.BoundedSemaphore(2)
_snapshot_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix='gaze-snapshot')
_snapshot_slots = threading.BoundedSemaphore(2)
_tracker_init_lock = threading.Lock()
_tracker_warmup_lock = threading.Lock()
_tracker_warmup_future = None
_GAZE_MODEL_FILENAMES = ('EfficientNetB0_gaze_float32.tflite', 'gaze_model_float32.tflite')


def _has_gaze_model(path: Path) -> bool:
    return any((path / filename).is_file() for filename in _GAZE_MODEL_FILENAMES)


def analyze_frame_bytes(raw):
    import cv2
    frame = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError('Invalid image')
    # lru_cache alone permits duplicate initialization on concurrent first calls.
    with _tracker_init_lock:
        tracker = get_gaze_tracker()
    if not tracker.ready:
        raise RuntimeError(tracker.error or 'Gaze model unavailable')
    return tracker.analyze(frame)


def submit_gaze_inference(analyzer, raw):
    """Keep one active and one waiting frame; reject excess stale work."""
    if not _inference_slots.acquire(blocking=False):
        return None
    try:
        future = GAZE_EXECUTOR.submit(analyzer, raw)
    except Exception:
        _inference_slots.release()
        raise
    future.add_done_callback(lambda _: _inference_slots.release())
    return future


def warm_gaze_tracker() -> bool:
    """Queue model initialization after Django is running, without blocking HTTP."""
    global _tracker_warmup_future
    if get_gaze_tracker.cache_info().currsize:
        return False
    with _tracker_warmup_lock:
        if get_gaze_tracker.cache_info().currsize:
            return False
        if _tracker_warmup_future and not _tracker_warmup_future.done():
            return False

        def initialize():
            try:
                with _tracker_init_lock:
                    return get_gaze_tracker()
            except Exception:
                logger.exception('Could not warm the gaze tracker')
                raise

        _tracker_warmup_future = GAZE_EXECUTOR.submit(initialize)
        return True


def sign_gaze_result(exam_id, email, raw, result):
    """Bind an analyzed result to the exact evidence frame and student."""
    return signing.dumps({
        'exam_id': int(exam_id), 'email': email.lower(),
        'image_sha256': hashlib.sha256(raw).hexdigest(), 'result': result.to_dict(),
    }, salt='gaze-frame', compress=True)


def read_gaze_result(receipt, exam_id, email, raw):
    try:
        data = signing.loads(receipt, salt='gaze-frame', max_age=15)
        if (data['exam_id'] != int(exam_id) or data['email'] != email.lower()
                or data['image_sha256'] != hashlib.sha256(raw).hexdigest()):
            raise signing.BadSignature('Gaze frame does not match its receipt')
        from gaze_tracker.tracker import GazeResult
        return GazeResult(**data['result'])
    except (KeyError, TypeError, ValueError) as exc:
        raise signing.BadSignature('Malformed gaze frame receipt') from exc


def schedule_live_snapshot(exam_id, email, raw):
    """Best-effort live preview: drop updates when storage is busy, never queue."""
    if not _snapshot_slots.acquire(blocking=False):
        return False

    def save():
        try:
            close_old_connections()
            save_live_snapshot(exam_id, email, raw)
        except Exception:
            logger.exception('Could not save live gaze snapshot')
        finally:
            close_old_connections()
            _snapshot_slots.release()

    try:
        _snapshot_executor.submit(save)
    except Exception:
        _snapshot_slots.release()
        raise
    return True

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _BACKEND_DIR.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))


def resolve_gaze_assets_dir() -> str:
    """Prefer GAZE_ASSETS_DIR, then exambackend assets, then TrainModel folder."""
    env = os.environ.get("GAZE_ASSETS_DIR")
    if env:
        p = Path(env)
        if p.is_dir() and _has_gaze_model(p):
            return str(p)

    backend_assets = _BACKEND_DIR / "gaze_tracker" / "assets"
    if _has_gaze_model(backend_assets):
        return str(backend_assets)

    train_assets = _REPO_ROOT / "TrainModel" / "gaze_tracker" / "assets"
    if _has_gaze_model(train_assets):
        return str(train_assets)

    return str(backend_assets)


@lru_cache(maxsize=1)
def get_gaze_tracker():
    """
    Returns the shared GazeTracker instance (model + MediaPipe loaded once).

    IMPORTANT: The tracker's internal temporal smoother is disabled here because
    the server handles many students concurrently on the same singleton instance.
    Per-submission smoothing is handled separately by `smooth_gaze_probs()`.
    """
    from gaze_tracker import GazeTracker

    return GazeTracker(
        assets_dir=resolve_gaze_assets_dir(),
        smoothing_window=1,   # Disable built-in smoother — we smooth per-submission below
        use_hysteresis=False,  # Disable built-in hysteresis — handled per-submission
    )


# ─────────────────────────────────────────────────────────────────────────────
# Per-submission temporal smoother
# ─────────────────────────────────────────────────────────────────────────────

_SMOOTHER_WINDOW = 2          # reduced from 4 — at 100ms polling, 4 frames = 400ms lag
_HYSTERESIS_EXIT_FRAMES = 1   # reduced from 2 — faster recovery to Normal
_HYSTERESIS_EXIT_CONF = 0.40  # dramatically reduced to prevent getting stuck in violation state

# submission_id (int) → {"buf": deque[np.ndarray], "violation": (idx,conf)|None, "normal_streak": int}
_per_submission_state: dict[int, dict] = {}
_state_lock = threading.Lock()

# Ramp weights for the rolling window (oldest → lowest weight)
_RAMP = np.arange(1, _SMOOTHER_WINDOW + 1, dtype=np.float32)


def _get_submission_state(submission_id: int) -> dict:
    with _state_lock:
        if submission_id not in _per_submission_state:
            _per_submission_state[submission_id] = {
                "buf": deque(maxlen=_SMOOTHER_WINDOW),
                "violation": None,
                "normal_streak": 0,
            }
        return _per_submission_state[submission_id]


def reset_submission_state(submission_id: int) -> None:
    """Call when a new exam attempt starts to clear stale smoothing state."""
    with _state_lock:
        _per_submission_state.pop(submission_id, None)


def save_live_snapshot(exam_set_id, student_email, img_bytes) -> None:
    """Write the live webcam still without overwriting is_done / score.

    ImageField.save(..., save=True) persists the whole in-memory row. A stale
    gaze worker would clobber a just-finished submission so the attempt never
    appeared until the student started again.
    """
    if not exam_set_id or not student_email or not img_bytes:
        return
    from django.core.files.base import ContentFile
    from django.utils import timezone
    from accounts.models import ExamSubmission

    sub = (
        ExamSubmission.objects.filter(
            exam_set_id=exam_set_id,
            student_email=student_email,
            is_done=False,
        )
        .only("id", "latest_snapshot")
        .first()
    )
    if not sub:
        return
    previous_name = sub.latest_snapshot.name
    filename = f"snapshot_{sub.id}.jpg"
    sub.latest_snapshot.save(filename, ContentFile(img_bytes), save=False)
    new_name = sub.latest_snapshot.name
    updated = ExamSubmission.objects.filter(
        pk=sub.pk, is_done=False, latest_snapshot=previous_name,
    ).update(
        latest_snapshot=sub.latest_snapshot.name,
        updated_at=timezone.now(),
    )
    storage = sub.latest_snapshot.storage
    if not updated:
        # The attempt ended or a newer snapshot won the race during upload.
        storage.delete(new_name)
    elif previous_name and previous_name != new_name:
        storage.delete(previous_name)


def smooth_gaze_probs(
    submission_id: int,
    raw_probs: dict[str, float],
    class_idx: int,
    confidence: float,
    classes: list[str],
    normal_idx: int,
) -> tuple[int, float]:
    """
    Per-submission smoothing has been disabled to eliminate lag and sticky states.
    The 5-second contiguous timer in views.py is completely sufficient to prevent 
    flickering without causing any responsiveness issues.
    """
    return class_idx, confidence


def gaze_tracker_status() -> dict:
    """Return whether the gaze model is loadable (for health checks)."""
    try:
        tracker = get_gaze_tracker()
        return {
            "ready": tracker.ready,
            "error": tracker.error,
            "assets_dir": resolve_gaze_assets_dir(),
        }
    except Exception as exc:
        return {
            "ready": False,
            "error": str(exc),
            "assets_dir": resolve_gaze_assets_dir(),
        }
