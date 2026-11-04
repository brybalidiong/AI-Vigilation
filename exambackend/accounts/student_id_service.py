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


def _read_text(image, page_mode=6, enhance=True):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    scale = min(2.0, 2200 / max(gray.shape))
    if abs(scale - 1) > .01:
        gray = cv2.resize(gray, None, fx=scale, fy=scale,
                          interpolation=cv2.INTER_CUBIC if scale > 1 else cv2.INTER_AREA)
    if enhance:
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
    first_joined = ''.join(first)
    last_joined = ''.join(last)
    # Printed and account names may split the same given name differently,
    # e.g. MARY ROSE on the ID and Maryrose in the account.
    lines = [_tokens(line) for line in printed_name.splitlines() if _tokens(line)]
    candidates = lines + [left + right for left, right in zip(lines, lines[1:])]
    for words in candidates:
        for first_end in range(1, min(len(words), len(first) + 2) + 1):
            if ''.join(words[:first_end]) != first_joined:
                continue
            for last_start in range(max(first_end, len(words) - len(last) - 1), len(words)):
                if ''.join(words[last_start:]) != last_joined:
                    continue
                # Permit one printed middle name or initial. More extra words
                # could indicate OCR joined unrelated text or another person.
                if last_start - first_end <= 1:
                    return True
    return False


def _school_matches(header_text):
    normalized = header_text.upper().replace('0', 'O').replace('1', 'I')
    words = _tokens(normalized)
    joined = ''.join(words)
    return 'DNSC' in words or (
        'DAVAO' in joined
        and (('NORTE' in joined and ('STATE' in joined or 'COLLEGE' in joined))
             or ('PANABO' in joined and 'STATE' in joined and 'COLLEGE' in joined))
    )


def _role_matches(text):
    return 'STUDENT' in ''.join(_tokens(text))


def _ocr_matches(image, matcher):
    for page_mode, enhance in ((6, True), (6, False), (11, False)):
        if matcher(_read_text(image, page_mode=page_mode, enhance=enhance)):
            return True
    return False


def _school_header_matches(image):
    height, width = image.shape[:2]
    regions = (
        image[:int(height * .28), :],
        image[int(height * .04):int(height * .35), int(width * .20):],
    )
    readings = []
    for region in regions:
        for page_mode, enhance in ((6, True), (6, False), (11, False)):
            reading = _read_text(region, page_mode=page_mode, enhance=enhance)
            readings.append(reading)
            if _school_matches(' '.join(readings)):
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

    if not _school_header_matches(image):
        raise StudentIdError('This does not appear to be a DNSC student ID. Upload the front of your DNSC ID.')
    role_image = image[int(height * .61):int(height * .77), :]
    if not _ocr_matches(role_image, _role_matches):
        raise StudentIdError('The student label could not be read. Retake the photo with the entire ID visible.')
    name_region = image[int(height * .52):int(height * .70), int(width * .05):int(width * .96)]
    if not _ocr_matches(name_region, lambda text: _name_matches(text, first_name, last_name)):
        raise StudentIdError('The name on the ID could not be matched to your account. Retake the photo or contact an administrator to correct your account name.')

    portrait = image[int(height * .23):int(height * .62), int(width * .14):int(width * .82)]
    features = _get_face_features(portrait, 'student ID portrait')
    if features is None:
        raise StudentIdError('The portrait on the ID could not be detected. Upload a clearer photo.')
    return features.flatten().tolist()
