"""Validate a DNSC student ID before using its portrait for exam face checks."""

import re
import subprocess
import unicodedata

import cv2
import numpy as np

from .face_service import _get_face_features, _load_image_bytes


class StudentIdError(ValueError):
    pass


def _tokens(value):
    ascii_text = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    return re.findall(r'[A-Z]+', ascii_text.upper())


def _read_text(image, page_mode=6):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
    ok, encoded = cv2.imencode('.png', gray)
    if not ok:
        raise StudentIdError('Could not read the student ID. Please upload a clearer image.')
    try:
        result = subprocess.run(
            ['tesseract', 'stdin', 'stdout', '-l', 'eng', '--psm', str(page_mode)],
            input=encoded.tobytes(), capture_output=True, timeout=12, check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        raise StudentIdError('Student ID reading is unavailable. Please try again later.') from exc
    if result.returncode:
        raise StudentIdError('Student ID reading is unavailable. Please try again later.')
    return result.stdout.decode('utf-8', errors='replace')


def _name_matches(printed_name, first_name, last_name):
    first = _tokens(first_name)
    last = _tokens(last_name)
    if not first or not last:
        return False
    expected = first + last
    # A middle name or initial may appear between the account's first and last names.
    for line in printed_name.splitlines():
        words = _tokens(line)
        if len(words) < len(expected) or len(words) > len(expected) + 2:
            continue
        if words[:len(first)] == first and words[-len(last):] == last:
            return True
    return False


def verify_student_id(image_bytes, first_name, last_name):
    """Return the ID portrait embedding; fail closed on unreadable or mismatched IDs."""
    if not image_bytes or len(image_bytes) > 5 * 1024 * 1024:
        raise StudentIdError('Upload a JPG or PNG student ID image under 5 MB.')
    image = _load_image_bytes(image_bytes)
    if image is None:
        raise StudentIdError('Could not read the student ID image. Upload a JPG or PNG photo.')
    height, width = image.shape[:2]
    if width < 500 or height < 750 or height / width < 1.25:
        raise StudentIdError('Upload a clear, upright photo of the entire student ID.')

    header = _tokens(_read_text(image[:int(height * .28), :]))
    if not (('DAVAO' in header and 'NORTE' in header and 'COLLEGE' in header) or 'DNSC' in header):
        raise StudentIdError('This does not appear to be a DNSC student ID. Upload the front of your DNSC ID.')
    role = _tokens(_read_text(image[int(height * .66):int(height * .79), :], 6))
    if 'STUDENT' not in role:
        raise StudentIdError('The student label could not be read. Retake the photo with the entire ID visible.')
    name_region = image[int(height * .57):int(height * .70), int(width * .10):int(width * .92)]
    printed_name = _read_text(name_region, 6)
    if not _name_matches(printed_name, first_name, last_name):
        raise StudentIdError('The name on the ID could not be matched to your account. Retake the photo or contact an administrator to correct your account name.')

    portrait = image[int(height * .23):int(height * .62), int(width * .14):int(width * .82)]
    features = _get_face_features(portrait, 'student ID portrait')
    if features is None:
        raise StudentIdError('The portrait on the ID could not be detected. Upload a clearer photo.')
    return features.flatten().tolist()
