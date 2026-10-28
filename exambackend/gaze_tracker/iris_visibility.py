"""Check whether the live image contains visible irises, independently of gaze labels."""

import cv2
import numpy as np


_EYES = (
    ((33, 133), (159, 145), 468),
    ((362, 263), (386, 374), 473),
)


def iris_visible(frame_bgr, landmarks):
    """Return True when at least one open eye has a discernible iris and sclera.

    MediaPipe can predict an iris through tinted lenses, so landmarks alone are
    insufficient. Compare actual pixels at the iris and on either side of it.
    A single clear eye is accepted to tolerate ordinary glasses and glare.
    """
    if len(landmarks) < 478:
        return False
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    height, width = gray.shape
    for (left, right), (top, bottom), iris in _EYES:
        x1, y1 = landmarks[left].x * width, landmarks[left].y * height
        x2, y2 = landmarks[right].x * width, landmarks[right].y * height
        eye_width = float(np.hypot(x2 - x1, y2 - y1))
        eye_height = float(np.hypot(
            (landmarks[top].x - landmarks[bottom].x) * width,
            (landmarks[top].y - landmarks[bottom].y) * height,
        ))
        if eye_width < 18 or eye_height / eye_width < 0.17:
            continue
        cx, cy = landmarks[iris].x * width, landmarks[iris].y * height
        radius = max(2, round(eye_width * 0.075))
        side_offset = round(eye_width * 0.29)

        def patch(x, y):
            ix, iy = round(x), round(y)
            return gray[max(0, iy - radius):min(height, iy + radius + 1),
                        max(0, ix - radius):min(width, ix + radius + 1)]

        pupil = patch(cx, cy)
        sides = (patch(cx - side_offset, cy), patch(cx + side_offset, cy))
        if not pupil.size or any(not side.size for side in sides):
            continue
        iris_level = float(np.median(pupil))
        sclera_level = max(float(np.median(side)) for side in sides)
        if sclera_level >= 42 and sclera_level - iris_level >= 12:
            return True
    return False
