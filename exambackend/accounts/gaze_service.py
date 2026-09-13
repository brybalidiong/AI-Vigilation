"""Lazy-loaded gaze tracker for exam proctoring."""
from __future__ import annotations

import os
import sys
import threading
from collections import deque
from functools import lru_cache
from pathlib import Path
from typing import Optional

import numpy as np

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _BACKEND_DIR.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))


def resolve_gaze_assets_dir() -> str:
    """Prefer GAZE_ASSETS_DIR, then exambackend assets, then TrainModel folder."""
    env = os.environ.get("GAZE_ASSETS_DIR")
    if env:
        p = Path(env)
        if p.is_dir() and (p / "gaze_model_float32.tflite").is_file():
            return str(p)

    backend_assets = _BACKEND_DIR / "gaze_tracker" / "assets"
    if (backend_assets / "gaze_model_float32.tflite").is_file():
        return str(backend_assets)

    train_assets = _REPO_ROOT / "TrainModel" / "gaze_tracker" / "assets"
    if (train_assets / "gaze_model_float32.tflite").is_file():
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
    filename = f"snapshot_{sub.id}.jpg"
    sub.latest_snapshot.save(filename, ContentFile(img_bytes), save=False)
    ExamSubmission.objects.filter(pk=sub.pk, is_done=False).update(
        latest_snapshot=sub.latest_snapshot.name,
        updated_at=timezone.now(),
    )


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
