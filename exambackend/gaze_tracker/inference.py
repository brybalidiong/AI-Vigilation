"""Gaze model preprocessing and label selection (must match Colab training)."""
from __future__ import annotations

import cv2
import numpy as np

# ImageNet normalisation constants — MUST match the albumentations Normalize
# call in colab_train.py: A.Normalize(mean=(0.485,0.456,0.406), std=(0.229,0.224,0.225))
# EfficientNetV2S is trained with these values, NOT with MobileNetV2 preprocess_input.
_IMG_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)  # RGB order
_IMG_STD  = np.array([0.229, 0.224, 0.225], dtype=np.float32)  # RGB order

LEFT_EYE_IDXS = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_IDXS = [362, 385, 387, 263, 373, 380]
LEFT_IRIS = [468, 469, 470, 471, 472]
RIGHT_IRIS = [473, 474, 475, 476, 477]
POSE_ANCHORS = [1, 152, 33, 263, 61, 291]

_GEO_MIRROR_IDXS = (5, 7)

_CENTER_H = 0.09
_CENTER_V = 0.10
_CENTER_IRIS_H = 0.09
_CENTER_IRIS_V = 0.10
_CENTER_HEAD_YAW = 0.18
_CENTER_HEAD_PITCH = 0.16

VIOLATION_CONFIDENCE_THRESHOLD = 0.34
LEFT_CONFIDENCE_THRESHOLD = 0.28
RIGHT_CONFIDENCE_THRESHOLD = 0.30
BELOW_CONFIDENCE_THRESHOLD = 0.34
ABOVE_VIOLATION_CONFIDENCE_THRESHOLD = 0.22
# Only used when Normal is nearly tied with a look-away — not to suppress a clear left/above.
_VIOLATION_OVER_NORMAL_MARGIN = 0.03

# Geometric decision boundaries (calibrated against real webcam footage)
# Sideways: ignore ordinary eye/head jitter near the centre. A deliberate side
# look still passes through either geometry agreement or a strong model score.
_SIDEWAYS_H = 0.075
_SIDEWAYS_YAW = 0.09
_HORIZONTAL_MODEL_ONLY_CONFIDENCE = 0.70
# Above: pitch + iris vertical position + blended vertical
_ABOVE_PITCH = 0.04          # lowered: fires with smaller upward head tilt
_ABOVE_IRIS_V = 0.018
_ABOVE_VERT = 0.040
# Below thresholds (relying primarily on iris movement to ignore camera angle)
_BELOW_PITCH = 0.40
_BELOW_IRIS_V = 0.11
_BELOW_VERT = 0.15
# Strong-geometry-only thresholds (fire without model confidence requirement)
_BELOW_PITCH_STRONG = 0.45  # Unused, pitch is too unreliable
_BELOW_IRIS_V_STRONG = 0.19
_ABOVE_IRIS_V_STRONG = 0.05  # lowered: geometry-only fires with less iris movement upward
# Strong-geometry-only sideways: both irises must agree on a clear movement.
_SIDEWAYS_IRIS_STRONG = 0.10


def prepare_image_batch(face_bgr: np.ndarray) -> np.ndarray:
    """
    Convert a BGR face crop to a float32 batch.
    EfficientNet handles its own normalisation internally, so we just
    pass it raw RGB values in the [0, 255] range as float32.
    """
    rgb = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2RGB)
    face_float = rgb.astype(np.float32)
    return np.expand_dims(face_float, axis=0)


def unmirror_face_crop(face_bgr: np.ndarray) -> np.ndarray:
    return cv2.flip(face_bgr, 1)


def mirror_correct_geo(geo: np.ndarray) -> np.ndarray:
    corrected = geo.copy()
    for idx in _GEO_MIRROR_IDXS:
        corrected[idx] *= -1.0
    # Iris X is measured in camera coordinates, but solvePnP yaw already has
    # the student's left/right sign. Rebuild the blended X after correcting
    # the irises instead of reversing the head pose as well.
    if geo[5] or geo[7]:
        iris_weight = max(float(geo[13]), 0.7)
        iris_h = (float(corrected[5]) + float(corrected[7])) / 2.0
        corrected[11] = iris_weight * iris_h + (1.0 - iris_weight) * float(corrected[0])
    return corrected


def extract_geometric_features(result, h, w) -> np.ndarray:
    feat = np.zeros(14, dtype=np.float32)
    if not result.face_landmarks:
        return feat

    lm = result.face_landmarks[0]
    pts = np.array([[l.x * w, l.y * h, l.z * w] for l in lm], dtype=np.float32)

    model_pts = np.array([
        [0, 0, 0],
        [0, -63.6, -12.5],
        [-43.3, 32.7, -26],
        [43.3, 32.7, -26],
        [-28.9, -28.9, -24.1],
        [28.9, -28.9, -24.1],
    ], dtype=np.float64)

    cam = np.array([
        [w, 0, w / 2],
        [0, w, h / 2],
        [0, 0, 1],
    ], dtype=np.float64)

    ok, rvec, _ = cv2.solvePnP(
        model_pts,
        pts[POSE_ANCHORS, :2].astype(np.float64),
        cam,
        np.zeros((4, 1)),
        flags=cv2.SOLVEPNP_ITERATIVE,
    )

    if not ok:
        return feat

    euler = cv2.RQDecomp3x3(cv2.Rodrigues(rvec)[0])[0]

    feat[0] = euler[1] / 180.0
    feat[1] = euler[0] / 180.0
    feat[2] = euler[2] / 180.0

    def ear(idx):
        e = pts[idx]
        return (
            np.linalg.norm(e[1] - e[5]) + np.linalg.norm(e[2] - e[4])
        ) / (2 * np.linalg.norm(e[0] - e[3]) + 1e-6)

    feat[3] = ear(LEFT_EYE_IDXS)
    feat[4] = ear(RIGHT_EYE_IDXS)

    if len(lm) >= 478:
        lc = pts[LEFT_IRIS].mean(0)[:2]
        rc = pts[RIGHT_IRIS].mean(0)[:2]
        le = pts[LEFT_EYE_IDXS].mean(0)[:2]
        re = pts[RIGHT_EYE_IDXS].mean(0)[:2]

        ls = np.linalg.norm(pts[LEFT_EYE_IDXS[0]] - pts[LEFT_EYE_IDXS[3]]) + 1e-6
        rs = np.linalg.norm(pts[RIGHT_EYE_IDXS[0]] - pts[RIGHT_EYE_IDXS[3]]) + 1e-6

        feat[5] = (lc[0] - le[0]) / ls
        feat[6] = (lc[1] - le[1]) / ls
        feat[7] = (rc[0] - re[0]) / rs
        feat[8] = (rc[1] - re[1]) / rs

        ec = float(min(feat[3], feat[4]) > 0.12) * min(1.0, feat[3] + feat[4])
        feat[9] = ec
        feat[10] = 1.0

        iris_h = (feat[5] + feat[7]) / 2.0
        iris_v = (feat[6] + feat[8]) / 2.0
        iris_weight = max(ec, 0.7)
        feat[11] = iris_weight * iris_h + (1.0 - iris_weight) * feat[0]
        feat[12] = iris_weight * iris_v + (1.0 - iris_weight) * feat[1]
        feat[13] = ec
    else:
        feat[10] = 1.0
        feat[11] = feat[0]
        feat[12] = feat[1]
        feat[13] = 0.5

    return feat


def _normal_class_index(classes: list) -> int:
    for i, name in enumerate(classes):
        if "normal" in name.lower():
            return i
    return 3


def _above_class_index(classes: list) -> int:
    for i, name in enumerate(classes):
        if "above" in name.lower():
            return i
    return 0


def _left_class_index(classes: list) -> int:
    for i, name in enumerate(classes):
        n = name.lower()
        if "left" in n and "right" not in n:
            return i
    return 1


def _right_class_index(classes: list) -> int:
    for i, name in enumerate(classes):
        n = name.lower()
        if "right" in n and "left" not in n:
            return i
    return 2


def _below_class_index(classes: list) -> int:
    for i, name in enumerate(classes):
        if "below" in name.lower():
            return i
    return 4


def _confidence_threshold_for_class_name(name: str) -> float:
    nl = name.lower()
    if "left" in nl and "right" not in nl:
        return LEFT_CONFIDENCE_THRESHOLD
    if "right" in nl and "left" not in nl:
        return RIGHT_CONFIDENCE_THRESHOLD
    if "above" in nl:
        return ABOVE_VIOLATION_CONFIDENCE_THRESHOLD
    if "below" in nl:
        return BELOW_CONFIDENCE_THRESHOLD
    return VIOLATION_CONFIDENCE_THRESHOLD


def _horizontal_side_for_name(name: str) -> str | None:
    nl = (name or '').lower()
    if 'left' in nl and 'right' not in nl:
        return 'left'
    if 'right' in nl and 'left' not in nl:
        return 'right'
    return None


def _horizontal_prediction_allowed(name: str, probability: float, geo: np.ndarray) -> bool:
    """Reject a horizontal model label caused only by near-centre jitter."""
    side = _horizontal_side_for_name(name)
    if not side:
        return True
    return (
        probability >= _HORIZONTAL_MODEL_ONLY_CONFIDENCE
        or is_looking_sideways(geo, side)
    )


def is_looking_sideways(geo: np.ndarray, side: str) -> bool:
    h = float(geo[11])
    yaw = float(geo[0])
    iris_h = (float(geo[5]) + float(geo[7])) / 2.0
    if side == "left":
        return h < -_SIDEWAYS_H or yaw < -_SIDEWAYS_YAW or iris_h < -_SIDEWAYS_H
    if side == "right":
        return h > _SIDEWAYS_H or yaw > _SIDEWAYS_YAW or iris_h > _SIDEWAYS_H
    return False


def is_looking_above(geo: np.ndarray, min_signals: int = 2) -> bool:
    """Return True when geometry indicates an upward gaze.

    Also handles the eyes-only case: when iris_v is very strongly negative
    (strong upward iris roll) even without head movement, we count it as
    satisfying 2 signals so pure eye-up looks are not missed.
    """
    pitch = float(geo[1])
    iris_v = (float(geo[6]) + float(geo[8])) / 2.0
    vert = float(geo[12])

    # Eyes-only fast path: iris rolled sharply upward with no head movement needed.
    # If iris_v is very strongly negative, treat it as 2-of-3 signals
    # so pure eye-up looks (common when reading notes above the screen) are caught.
    if iris_v < -0.035:
        return True

    signals = (
        int(pitch < -_ABOVE_PITCH)
        + int(iris_v < -_ABOVE_IRIS_V)
        + int(vert < -_ABOVE_VERT)
    )
    return signals >= min_signals


def is_looking_below(geo: np.ndarray) -> bool:
    """Return True when geometry clearly indicates a downward gaze.

    Requires 2-of-3 signals to agree to reduce false positives — a single
    raised iris value or slight head nod during normal speech is common noise.
    """
    pitch = float(geo[1])
    iris_v = (float(geo[6]) + float(geo[8])) / 2.0
    vert = float(geo[12])

    # UNIVERSAL LOCK: If the irises are rolled UP relative to the lens,
    # it is impossible to be "looking below" the lens.
    if iris_v < -0.02:
        return False

    # Quick-fire shortcut: iris must be very clearly down AND head pitched noticeably.
    # Both thresholds are intentionally high — normal reading or typing posture
    # should never cross both simultaneously.
    if iris_v > 0.095 and pitch > 0.10:
        return True

    signals = (
        int(pitch > _BELOW_PITCH)
        + int(iris_v > _BELOW_IRIS_V)
        + int(vert > _BELOW_VERT)
    )
    return signals >= 2


def is_looking_above_strong(geo: np.ndarray) -> bool:
    """Stricter version: geometry alone is overwhelmingly clear, no model needed."""
    iris_v = (float(geo[6]) + float(geo[8])) / 2.0
    return iris_v < -_ABOVE_IRIS_V_STRONG


def is_looking_below_strong(geo: np.ndarray) -> bool:
    """Stricter version: geometry alone is overwhelmingly clear, no model needed."""
    iris_v = (float(geo[6]) + float(geo[8])) / 2.0
    
    # Pitch is utterly unreliable due to variable webcam heights.
    # We only trust extreme downward iris movement.
    return iris_v > _BELOW_IRIS_V_STRONG


def _pick_sideways_from_geometry(
    geo: np.ndarray,
    left_idx: int,
    right_idx: int,
    left_p: float,
    right_p: float,
    above_p: float,
) -> tuple[int, float] | None:
    left_geo = is_looking_sideways(geo, "left")
    right_geo = is_looking_sideways(geo, "right")
    
    # 1. Pure geometry override (extreme eye movement, even if CNN is unsure)
    left_iris = float(geo[5])
    right_iris = float(geo[7])
    iris_h = (left_iris + right_iris) / 2.0
    if (abs(iris_h) >= _SIDEWAYS_IRIS_STRONG
            and left_iris * right_iris > 0):
        # Geometry is in selfie coordinates: negative X is the student's left.
        if iris_h < 0:
            return left_idx, max(left_p, 0.50)
        else:
            return right_idx, max(right_p, 0.50)

    # 2. Require BOTH geometry AND model agreement to reduce false positives
    if left_geo and left_p >= LEFT_CONFIDENCE_THRESHOLD:
        if not right_geo or left_p >= right_p:
            return left_idx, left_p
    if right_geo and right_p >= RIGHT_CONFIDENCE_THRESHOLD:
        return right_idx, right_p

    # Stronger geometry fallback: require a more definitive head position
    h = float(geo[11])
    if h < -0.065 and left_p >= LEFT_CONFIDENCE_THRESHOLD and left_p >= right_p:
        return left_idx, left_p
    if h > 0.065 and right_p >= RIGHT_CONFIDENCE_THRESHOLD and right_p >= left_p:
        return right_idx, right_p

    return None


def _strong_sideways_from_geometry(geo: np.ndarray) -> str | None:
    """Return a student's-perspective side only for unambiguous geometry.

    This is intentionally stricter than the normal geometry fallback. It is a
    consistency check for the CNN: when a clear iris/head movement disagrees
    with a horizontal CNN class, the camera geometry prevents a left/right
    label inversion from reaching the user.
    """
    left_iris = float(geo[5])
    right_iris = float(geo[7])
    iris_h = (left_iris + right_iris) / 2.0
    if (abs(iris_h) >= _SIDEWAYS_IRIS_STRONG
            and left_iris * right_iris > 0):
        return "left" if iris_h < 0 else "right"
    if abs(float(geo[0])) >= 0.14:
        return "left" if float(geo[0]) < 0 else "right"
    return None


def is_looking_at_screen(geo: np.ndarray) -> bool:
    iris_h = (float(geo[5]) + float(geo[7])) / 2.0
    iris_v = (float(geo[6]) + float(geo[8])) / 2.0
    return (
        abs(float(geo[11])) < _CENTER_H
        and abs(float(geo[12])) < _CENTER_V
        and abs(iris_h) < _CENTER_IRIS_H
        and abs(iris_v) < _CENTER_IRIS_V
        and abs(float(geo[0])) < _CENTER_HEAD_YAW
        and abs(float(geo[1])) < _CENTER_HEAD_PITCH
    )


def pick_gaze_label(predictions: np.ndarray, geo: np.ndarray, classes: list) -> tuple[int, float]:
    """
    Pick gaze class from CNN probabilities, with geometry as a tie-break.

    If Normal is the strongest class, return Normal immediately (prevents sticky
    look-aways). A clear left/above/right/below argmax is trusted even if head
    pose is only mildly off-center.
    """
    probs = np.asarray(predictions, dtype=np.float32)
    normal_idx = _normal_class_index(classes)
    normal_conf = float(probs[normal_idx])
    looking_center = is_looking_at_screen(geo)
    argmax_idx = int(np.argmax(probs))

    # Use only very clear geometry to reconcile a horizontal CNN prediction.
    # This corrects camera/model mirror mismatches while leaving normal and
    # borderline frames to the confidence-based classifier below.
    strong_side = _strong_sideways_from_geometry(geo)
    if strong_side:
        side_idx = _left_class_index(classes) if strong_side == "left" else _right_class_index(classes)
        side_name = classes[side_idx].lower()
        argmax_name = classes[argmax_idx].lower()
        argmax_is_left = "left" in argmax_name and "right" not in argmax_name
        argmax_is_right = "right" in argmax_name and "left" not in argmax_name
        if ((strong_side == "left" and not argmax_is_left)
                or (strong_side == "right" and not argmax_is_right)):
            # Geometry also wins over a Normal argmax when the eye movement is
            # unambiguous. Keep a conservative but valid confidence value.
            return side_idx, max(float(probs[side_idx]), 0.50)

    if argmax_idx == normal_idx:
        return normal_idx, normal_conf

    if (looking_center and float(probs[argmax_idx]) < normal_conf + 0.08
            and not is_looking_above(geo) and not is_looking_below(geo)):
        return normal_idx, normal_conf

    def _below_blocked(name: str) -> bool:
        if "below" not in name.lower():
            return False
        iris_v = (float(geo[6]) + float(geo[8])) / 2.0
        return iris_v < -0.02

    argmax_name = classes[argmax_idx]
    argmax_p = float(probs[argmax_idx])
    if (
        not _below_blocked(argmax_name)
        and _horizontal_prediction_allowed(argmax_name, argmax_p, geo)
        and argmax_p >= _confidence_threshold_for_class_name(argmax_name)
    ):
        return argmax_idx, argmax_p

    best: tuple[int, float] | None = None
    for idx, name in enumerate(classes):
        if idx == normal_idx:
            continue
        prob = float(probs[idx])
        if prob < _confidence_threshold_for_class_name(name):
            continue
        if not _horizontal_prediction_allowed(name, prob, geo):
            continue
        if _below_blocked(name):
            continue
        if best is None or prob > best[1]:
            best = (idx, prob)

    if best is not None and best[1] >= normal_conf + _VIOLATION_OVER_NORMAL_MARGIN:
        return best

    left_idx = _left_class_index(classes)
    right_idx = _right_class_index(classes)
    above_idx = _above_class_index(classes)
    below_idx = _below_class_index(classes)
    left_p = float(probs[left_idx])
    right_p = float(probs[right_idx])
    above_p = float(probs[above_idx])
    below_p = float(probs[below_idx])

    sideways = _pick_sideways_from_geometry(
        geo, left_idx, right_idx, left_p, right_p, above_p,
    )
    if sideways is not None and sideways[1] >= normal_conf * 0.85:
        return sideways

    if is_looking_sideways(geo, "left") and left_p >= 0.22 and left_p >= right_p:
        return left_idx, left_p
    if is_looking_sideways(geo, "right") and right_p >= 0.22 and right_p >= left_p:
        return right_idx, right_p

    if is_looking_above(geo, min_signals=1) and above_p >= 0.22 and above_p >= normal_conf * 0.8:
        return above_idx, above_p
    if is_looking_above_strong(geo) and above_p >= 0.18:
        return above_idx, max(above_p, 0.50)
    if is_looking_below(geo) and below_p >= 0.28 and below_p >= normal_conf * 0.85:
        return below_idx, below_p

    return normal_idx, normal_conf
