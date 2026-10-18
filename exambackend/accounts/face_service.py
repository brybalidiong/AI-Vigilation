"""
face_service.py
---------------
Face verification using OpenCV YuNet (detection) + SFace (recognition).
No cloud APIs, no TensorFlow — pure OpenCV ONNX inference.

Performance note: YuNet and SFace are cached as module-level singletons so
the ONNX models are loaded from disk only ONCE per server process, not on
every request. This reduces per-request overhead from ~1–3 s down to <50 ms.
"""
import cv2
import json
import logging
import os
import tempfile
import threading
import numpy as np

from django.conf import settings

logger = logging.getLogger(__name__)
face_logger = logger

# Paths to the ONNX models downloaded to exambackend/models/
BASE_DIR = getattr(settings, 'BASE_DIR', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FACE_MODELS_DIR = os.getenv('FACE_MODELS_DIR') or os.path.join(BASE_DIR, 'models')
YUNET_MODEL_PATH = os.path.join(FACE_MODELS_DIR, 'yunet.onnx')
SFACE_MODEL_PATH = os.path.join(FACE_MODELS_DIR, 'sface.onnx')

# Thresholds
# Lower = more permissive. Profile photos vs webcam images need a lenient threshold.
_DETECT_THRESHOLD = 0.35  # YuNet score threshold (lowered for webcam images)
_MATCH_THRESHOLD  = 0.10  # SFace cosine similarity threshold (lowered for better matching)

# Max dimension for YuNet to prevent huge memory usage, aspect ratio will be preserved
_YUNET_MAX_SIZE = 640

# ---------------------------------------------------------------------------
# Singleton model cache — load ONCE per process, reuse on every request.
# ---------------------------------------------------------------------------
_model_lock = threading.Lock()

# SFace recognizer: stateless w.r.t. image size → single instance is enough.
_recognizer_singleton = None

# YuNet detector: must be told (width, height) at creation time.
# Cache the last-used size; re-create only when size changes (cheap).
_detector_singleton = None
_detector_input_size = None   # (w, h)


def _get_recognizer():
    """Return the cached SFace recognizer, creating it on first call."""
    global _recognizer_singleton
    if _recognizer_singleton is not None:
        return _recognizer_singleton
    if not os.path.exists(SFACE_MODEL_PATH):
        logger.error("[face_service] SFace model missing: %s", SFACE_MODEL_PATH)
        return None
    with _model_lock:
        if _recognizer_singleton is None:   # double-checked locking
            face_logger.info("Loading SFace recognizer from %s ...", SFACE_MODEL_PATH)
            _recognizer_singleton = cv2.FaceRecognizerSF.create(
                model=SFACE_MODEL_PATH, config=""
            )
            face_logger.info("SFace recognizer loaded OK.")
    return _recognizer_singleton


def _get_detector(w, h):
    """Return a YuNet detector sized for (w, h), re-creating only on size change."""
    global _detector_singleton, _detector_input_size
    if not os.path.exists(YUNET_MODEL_PATH):
        logger.error("[face_service] YuNet model missing: %s", YUNET_MODEL_PATH)
        return None
    target_size = (w, h)
    with _model_lock:
        if _detector_singleton is None or _detector_input_size != target_size:
            face_logger.info(
                "Creating YuNet detector for size %s (prev=%s)...",
                target_size, _detector_input_size,
            )
            _detector_singleton = cv2.FaceDetectorYN.create(
                model=YUNET_MODEL_PATH,
                config="",
                input_size=(w, h),
                score_threshold=_DETECT_THRESHOLD,
                nms_threshold=0.3,
                top_k=5000,
            )
            _detector_input_size = target_size
            face_logger.info("YuNet detector ready.")
    return _detector_singleton


def _load_image_bgr(image_path: str) -> np.ndarray | None:
    """Load any image to BGR numpy array."""
    img = cv2.imread(image_path)
    if img is None:
        try:
            raw = np.fromfile(image_path, dtype=np.uint8)
            img = cv2.imdecode(raw, cv2.IMREAD_COLOR)
        except Exception:
            pass
    if img is None:
        logger.error(f"[face_service] cv2.imread failed on {image_path}")
        return None
    if len(img.shape) == 3 and img.shape[2] == 4:
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    return img


def _load_image_bytes(raw: bytes) -> np.ndarray | None:
    """Decode an uploaded image in memory, avoiding temporary disk I/O."""
    if not raw:
        return None
    try:
        img = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
    except Exception:
        img = None
    return img


def _get_face_features(img, label="image"):
    """
    Detects the largest face using YuNet and extracts a 128-dim SFace embedding.
    Uses cached singleton models — no disk I/O after the first call.
    Returns the embedding as a (1, 128) float32 ndarray, or None on failure.
    """
    recognizer = _get_recognizer()
    if recognizer is None:
        logger.error("[face_service] SFace recognizer unavailable.")
        return None

    try:
        h, w = img.shape[:2]

        # Scale down large images while PRESERVING aspect ratio
        scale = 1.0
        if max(h, w) > _YUNET_MAX_SIZE:
            scale = _YUNET_MAX_SIZE / max(h, w)

        new_w, new_h = int(w * scale), int(h * scale)
        resized = cv2.resize(img, (new_w, new_h)) if scale != 1.0 else img.copy()

        # Reuse the cached detector (re-creates only when size changes — cheap)
        detector = _get_detector(new_w, new_h)
        if detector is None:
            return None

        _, faces = detector.detect(resized)
        if faces is None or len(faces) == 0:
            face_logger.info(f"YuNet: NO face detected in {label} (threshold={_DETECT_THRESHOLD})")
            return None

        # Scale face coordinates back to original image size for alignCrop
        face = faces[0].copy()
        if scale != 1.0:
            face[0] /= scale   # x
            face[1] /= scale   # y
            face[2] /= scale   # width
            face[3] /= scale   # height
            # Scale landmarks (5 points x 2 coords, starting at index 4)
            for i in range(5):
                face[4 + i * 2]     /= scale
                face[4 + i * 2 + 1] /= scale

        face_logger.info(f"YuNet: face detected (score={faces[0][14]:.3f}) in {label}")

        aligned = recognizer.alignCrop(img, face)
        features = recognizer.feature(aligned)
        return features

    except Exception:
        import traceback
        face_logger.error(f"_get_face_features error on {label}:\n%s", traceback.format_exc())
        return None


def extract_face_encoding(image_path):
    """
    Extracts face features as a flat Python list suitable for JSON storage.
    Returns None if no face is detected.
    """
    img = _load_image_bgr(image_path)
    if img is None:
        return None
    features = _get_face_features(img, os.path.basename(image_path))
    if features is not None:
        flat = features.flatten().tolist()
        face_logger.info(f"Encoding extracted: {len(flat)} dims")
        return flat
    return None


def extract_face_encoding_bytes(image_bytes):
    """Extract features from storage-backed images without requiring a local path."""
    img = _load_image_bytes(image_bytes)
    if img is None:
        return None
    features = _get_face_features(img, "stored image")
    return features.flatten().tolist() if features is not None else None


def verify_face(stored_encoding_json, webcam_image_path):
    """
    Compare a stored face embedding (JSON) against a new webcam image.
    Tries original and flipped version to account for potential mirroring.
    Uses cached singleton models — fast after the first call.
    """
    img = _load_image_bgr(webcam_image_path)
    return _verify_face_image(stored_encoding_json, img)


def verify_face_bytes(stored_encoding_json, webcam_image_bytes):
    """Compare a stored embedding with an uploaded image held in memory."""
    return _verify_face_image(stored_encoding_json, _load_image_bytes(webcam_image_bytes))


def _verify_face_image(stored_encoding_json, img):
    recognizer = _get_recognizer()
    if recognizer is None:
        return {"verified": False, "error": "Face recognition model unavailable."}

    try:
        stored_list = json.loads(stored_encoding_json)
        stored_features = np.array(stored_list, dtype=np.float32).reshape(1, -1)

        if img is None:
            return {"verified": False, "error": "Could not read webcam image."}

        # Browser canvas captures raw camera pixels. Use that normal orientation
        # first and pay for a mirrored fallback only when it does not verify.
        best_score = -1.0
        for label, img_data in (("original", img), ("flipped", cv2.flip(img, 1))):
            feats = _get_face_features(img_data, f"webcam_{label}")
            if feats is not None:
                score = float(recognizer.match(
                    stored_features, feats, cv2.FaceRecognizerSF_FR_COSINE
                ))
                face_logger.info(f"Comparison ({label}): score={score:.4f}")
                best_score = max(best_score, score)
                if best_score >= _MATCH_THRESHOLD:
                    break

        if best_score == -1.0:
            return {
                "verified": False,
                "error": "No face detected in webcam image. Please check lighting/visibility.",
            }

        is_identical = best_score >= _MATCH_THRESHOLD
        face_logger.info(
            f"Final Verification -> best_score={best_score:.4f}, "
            f"threshold={_MATCH_THRESHOLD}, verified={is_identical}"
        )

        return {
            "verified": is_identical,
            "distance": round(1.0 - best_score, 4),
            "confidence": round(best_score * 100, 2),
            "error": None,
        }

    except Exception:
        import traceback
        face_logger.error("[face_service] verify_face exception: %s", traceback.format_exc())
        return {"verified": False, "error": "Verification error. Please try again."}


def save_temp_image(django_uploaded_file) -> str:
    """
    Saves a Django UploadedFile to a temp file on disk.
    Caller must delete the file when done.
    """
    suffix = os.path.splitext(django_uploaded_file.name)[-1] or ".jpg"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    for chunk in django_uploaded_file.chunks():
        tmp.write(chunk)
    tmp.close()
    return tmp.name
