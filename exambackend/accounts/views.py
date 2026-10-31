from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.db.models import Count, Exists, Q
from django.http import FileResponse
from django.utils import timezone
from django.utils.crypto import salted_hmac
from django.utils.dateparse import parse_date, parse_datetime
from datetime import datetime, time, timedelta
import re
from firebase_admin import auth as firebase_auth
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
import copy
import csv
import io
import hashlib
from zipfile import BadZipFile

from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException
from PIL import Image, UnidentifiedImageError

import accounts.firebase_admin  # noqa: F401
from decimal import Decimal, InvalidOperation

from .grading import grade_question
from .exam_updates import notify_exam_published
from .models import (
    ExamIntegrityReport,
    GazeModelSelection,
    ExamProctoringEvent,
    ExamProctoringEvidence,
    ExamQuestion,
    QuestionBankBatch,
    QuestionBankItem,
    ExamSet,
    ExamSubmission,
    EnrolledStudent,
    StudentAnswer,
    StudentSet,
    Subject,
    SubjectEnrollment,
    UserProfile,
)


def _sync_profile_enrollment_for_email(email: str):
    # Enrollment is now strictly controlled by the admin.
    pass


def _enroll_student_in_set_once(email: str, roster: StudentSet):
    """Keep one course enrollment even when instructors use different rosters."""
    with transaction.atomic():
        if roster.subject_id:
            # Serialize enrollments for this course across its instructors.
            Subject.objects.select_for_update().get(pk=roster.subject_id)
            existing = EnrolledStudent.objects.filter(
                email__iexact=email,
                student_set__subject_id=roster.subject_id,
            ).select_related('student_set').first()
        else:
            existing = EnrolledStudent.objects.filter(
                email__iexact=email,
                student_set=roster,
            ).first()
        if existing:
            return None, existing
        return EnrolledStudent.objects.create(email=email, student_set=roster), None



def _is_instructor(user):
    return bool(user and user.is_authenticated and user.is_active and user.is_staff and not user.is_superuser)


def _effective_face_status(profile):
    return (UserProfile.FACE_STATUS_APPROVED if profile and profile.id_verified_at
            and profile.face_photo and profile.face_encoding
            and profile.face_status == UserProfile.FACE_STATUS_APPROVED
            else UserProfile.FACE_STATUS_NONE)


PROCTORING_EVENT_PENALTIES = {
    ExamProctoringEvent.EVENT_TAB_SWITCH: 12,
    ExamProctoringEvent.EVENT_WINDOW_BLUR: 4,
    ExamProctoringEvent.EVENT_SPLIT_SCREEN: 8,
    ExamProctoringEvent.EVENT_EXTENDED_MONITOR: 10,
    ExamProctoringEvent.EVENT_COPY_ATTEMPT: 5,
    ExamProctoringEvent.EVENT_CUT_ATTEMPT: 5,
    ExamProctoringEvent.EVENT_SCREENSHOT_ATTEMPT: 10,
    ExamProctoringEvent.EVENT_SCREEN_SHARE_STOPPED: 12,
    ExamProctoringEvent.EVENT_RIGHT_CLICK: 3,
    ExamProctoringEvent.EVENT_GAZE_VIOLATION: 6,
    ExamProctoringEvent.EVENT_GAZE_NO_FACE: 8,
    ExamProctoringEvent.EVENT_GADGET_DETECTED: 15,
    ExamProctoringEvent.EVENT_EXAM_TERMINATED: 25,
}

# Auto-terminate exam when gaze strikes reach these limits (each logged strike ≈ 5s apart).
GAZE_VIOLATION_TERMINATE_LIMIT = 8
GAZE_NO_FACE_TERMINATE_LIMIT = 5
GAZE_CONFIDENCE_THRESHOLD = 0.34
GAZE_ABOVE_CONFIDENCE_THRESHOLD = 0.22  # lowered from 0.26 to match inference.py
GAZE_LEFT_CONFIDENCE_THRESHOLD = 0.28
GAZE_RIGHT_CONFIDENCE_THRESHOLD = 0.30
GAZE_BELOW_CONFIDENCE_THRESHOLD = 0.25
GAZE_LEFT_RIGHT_CONTINUOUS_SECONDS = 4.0   # raised: flag at ~4-5s real-world
GAZE_ABOVE_CONTINUOUS_SECONDS = 4.0        # raised: flag at ~4-5s real-world
GAZE_BELOW_CONTINUOUS_SECONDS = 4.0        # raised: flag at ~4-5s real-world
GAZE_CONTINUOUS_SECONDS = 4.0              # raised: flag at ~4-5s real-world
GAZE_NO_FACE_HOLD_SECONDS = 10
GAZE_GLANCE_CONFIDENCE = 0.90


def _gaze_glances_per_violation(exam_set) -> int:
    """Use the configured exam duration for the shared brief-gaze limit."""
    minutes = exam_set.time_limit
    if minutes == 0 or minutes >= 120:
        return 15
    if minutes < 30:
        return 5
    return 10

# In-memory: (submission_id, attempt) -> {label, at} for continuous gaze strikes.
_GAZE_PENDING_STRIKES: dict[tuple[int, int], dict] = {}
# One no-face strike per absence episode; hold exam after 10s without a face.
_GAZE_NO_FACE_ABSENCE: dict[tuple[int, int], dict] = {}
# Cached strike counts — refreshed from DB only when a new strike is logged.
_GAZE_STRIKE_CACHE: dict[tuple[int, int], dict] = {}
# Tracks when we last saw a suspicious frame — used for grace-period-based clearing.
_GAZE_LAST_SUSPICIOUS: dict[tuple[int, int], object] = {}
# One high-confidence count per gaze episode; persisted tally lives on the submission.
_GAZE_GLANCE_EPISODES: dict[tuple[int, int], dict] = {}
# Immediate gadget warnings; terminate after this many logged detections.
GADGET_WARNING_TERMINATE_LIMIT = 3
# Ignore back-to-back frames so one continuous hold is one warning.
_GADGET_WARNING_COOLDOWN_SECONDS = 3.0
_GADGET_INFER_TIMEOUT_SECONDS = 45
# In-memory: (submission_id, attempt) -> {last_logged, cleared, warning_count}
_GADGET_DETECTION_STATE: dict[tuple[int, int], dict] = {}


def _gadget_now_timestamp() -> float:
    return timezone.now().timestamp()


def _gadget_warning_count(submission, force_refresh: bool = False) -> int:
    """Count logged gadget warnings for the current attempt."""
    key = (submission.pk, submission.attempt_count)
    state = _GADGET_DETECTION_STATE.setdefault(key, {
        'last_logged': 0.0,
        'cleared': True,
        'warning_count': None,
    })
    if not force_refresh and state.get('warning_count') is not None:
        return int(state['warning_count'])
    count = ExamProctoringEvent.objects.filter(
        submission=submission,
        attempt_number=submission.attempt_count,
        event_type=ExamProctoringEvent.EVENT_GADGET_DETECTED,
    ).count()
    state['warning_count'] = count
    return count


# Tracks when each submission last logged a gaze violation — enforces server-side cooldown.
_GAZE_LAST_LOGGED: dict[tuple[int, int], object] = {}
GAZE_VIOLATION_COOLDOWN_SECONDS = 6.0  # match WS_VIOLATION_COOLDOWN_MS on the frontend


def _gaze_pending_key(submission) -> tuple[int, int]:
    return (submission.pk, submission.attempt_count)


def _clear_gaze_pending(submission) -> None:
    key = _gaze_pending_key(submission)
    _GAZE_PENDING_STRIKES.pop(key, None)
    _GAZE_LAST_SUSPICIOUS.pop(key, None)


def _gaze_mark_suspicious(submission, now) -> None:
    """Record that we just saw a suspicious frame for this submission."""
    _GAZE_LAST_SUSPICIOUS[_gaze_pending_key(submission)] = now


def _gaze_normal_long_enough(submission, now, grace_seconds: float = 1.5) -> bool:
    """Return True only if we haven't seen a suspicious frame for grace_seconds.
    Prevents a single flickering normal frame from resetting the continuous timer.
    """
    key = _gaze_pending_key(submission)
    last = _GAZE_LAST_SUSPICIOUS.get(key)
    if last is None:
        return True  # Never been suspicious — safe to clear
    return (now - last).total_seconds() >= grace_seconds


def _gaze_mark_violation_logged(submission, now) -> None:
    """Record that a gaze violation was just logged. Starts the server-side cooldown."""
    _GAZE_LAST_LOGGED[_gaze_pending_key(submission)] = now


def _gaze_in_violation_cooldown(submission, now) -> bool:
    """True if a violation was logged recently and the cooldown hasn't expired.
    Prevents the HTTP polling loop from double-logging after the WS fires a strike.
    """
    key = _gaze_pending_key(submission)
    last = _GAZE_LAST_LOGGED.get(key)
    if last is None:
        return False
    return (now - last).total_seconds() < GAZE_VIOLATION_COOLDOWN_SECONDS


def _clear_no_face_absence(submission) -> None:
    _GAZE_NO_FACE_ABSENCE.pop(_gaze_pending_key(submission), None)


def _gaze_pending_elapsed(submission) -> float:
    """Return seconds since the current pending gaze-direction violation first appeared.
    Returns 0.0 if no pending violation is being tracked (normal state).
    """
    key = _gaze_pending_key(submission)
    pending = _GAZE_PENDING_STRIKES.get(key)
    if not pending:
        return 0.0
    return max(0.0, (timezone.now() - pending['at']).total_seconds())


def _is_left_right_label(label: str) -> bool:
    l = (label or '').lower()
    return ('left' in l and 'right' not in l) or ('right' in l and 'left' not in l)


def _is_above_label(label: str) -> bool:
    return 'above' in (label or '').lower()


def _is_below_label(label: str) -> bool:
    return 'below' in (label or '').lower()


def _gaze_continuous_seconds_for_label(label: str) -> float:
    if _is_left_right_label(label):
        return GAZE_LEFT_RIGHT_CONTINUOUS_SECONDS
    if _is_above_label(label):
        return GAZE_ABOVE_CONTINUOUS_SECONDS
    if _is_below_label(label):
        return GAZE_BELOW_CONTINUOUS_SECONDS
    return GAZE_CONTINUOUS_SECONDS


def _gaze_continuous_slack_seconds(label: str) -> float:
    """No slack — the full threshold must elapse before firing a strike."""
    return 0.0


def _gaze_continuous_strike_ready(submission, label: str) -> bool:
    """True when ANY look-away has been held for the required duration.

    The timer starts on the first suspicious frame and fires once the required
    number of seconds has elapsed — even if the specific direction changes
    between frames (e.g., Left -> Above -> Left all count as continuous).
    On fire the timer is cleared; the caller must restart it if needed.
    """
    continuous_seconds = _gaze_continuous_seconds_for_label(label)
    key = _gaze_pending_key(submission)
    pending = _GAZE_PENDING_STRIKES.get(key)
    now = timezone.now()
    if pending:
        elapsed = (now - pending['at']).total_seconds()
        slack = _gaze_continuous_slack_seconds(label)
        if elapsed >= continuous_seconds - slack:
            _GAZE_PENDING_STRIKES.pop(key, None)
            return True
        # Keep original start time; update label to most recent direction
        pending['label'] = label
        return False
    _GAZE_PENDING_STRIKES[key] = {'label': label, 'at': now}
    return False


def _process_no_face_absence(submission, is_no_face: bool) -> dict:
    """Track absence episodes: one strike per episode; hold after 10s."""
    key = _gaze_pending_key(submission)
    now = timezone.now()
    if not is_no_face:
        _clear_no_face_absence(submission)
        return {
            'hold_exam': False,
            'absent_seconds': 0.0,
            'should_log_strike': False,
        }

    state = _GAZE_NO_FACE_ABSENCE.get(key)
    if not state:
        state = {'started_at': now, 'flagged': False}
        _GAZE_NO_FACE_ABSENCE[key] = state

    absent_seconds = (now - state['started_at']).total_seconds()
    should_log_strike = not state['flagged']
    if should_log_strike:
        state['flagged'] = True

    return {
        'hold_exam': absent_seconds >= GAZE_NO_FACE_HOLD_SECONDS,
        'absent_seconds': absent_seconds,
        'should_log_strike': should_log_strike,
    }


def _gaze_violation_confidence_ok(label: str, confidence: float) -> bool:
    if _is_above_label(label):
        return confidence >= GAZE_ABOVE_CONFIDENCE_THRESHOLD
    l = label.lower()
    if 'left' in l and 'right' not in l:
        return confidence >= GAZE_LEFT_CONFIDENCE_THRESHOLD
    if 'right' in l and 'left' not in l:
        return confidence >= GAZE_RIGHT_CONFIDENCE_THRESHOLD
    if _is_below_label(label):
        return confidence >= GAZE_BELOW_CONFIDENCE_THRESHOLD
    return confidence >= GAZE_CONFIDENCE_THRESHOLD


def _high_confidence_gaze_direction(result, enabled: bool) -> str:
    """Only a visible, enabled look-away above 90% can enter the shared tally."""
    if not enabled or not result.face_detected or result.confidence <= GAZE_GLANCE_CONFIDENCE:
        return ''
    label = str(result.label or '').lower()
    if 'above' in label:
        return 'above'
    if 'below' in label:
        return 'below'
    if 'left' in label and 'right' not in label:
        return 'left'
    if 'right' in label and 'left' not in label:
        return 'right'
    return ''


def _new_gaze_glance_episode(submission, direction: str, *, from_websocket: bool) -> bool:
    """Deduplicate a held gaze; two neutral observations rearm the same direction."""
    key = _gaze_pending_key(submission)
    state = _GAZE_GLANCE_EPISODES.setdefault(key, {'direction': '', 'neutral': 0})
    if not direction:
        state['neutral'] += 1
        if state['neutral'] >= 2:
            state['direction'] = ''
        return False
    state['neutral'] = 0
    if from_websocket:
        # The WebSocket client reports only a new episode, including the first
        # high-confidence horizontal frame before its normal timer stabilizes.
        state['direction'] = direction
        return True
    if state['direction'] == direction:
        return False
    state['direction'] = direction
    return True


def _increment_gaze_glance_count(submission, raw: bytes, threshold: int) -> tuple[bool, bool]:
    """Persist the shared tally, ignoring repeat uploads of the same signed frame."""
    frame_hash = hashlib.sha256(raw).hexdigest()
    with transaction.atomic():
        locked = ExamSubmission.objects.select_for_update().get(pk=submission.pk)
        if locked.gaze_glance_last_frame_hash == frame_hash:
            submission.gaze_glance_count = locked.gaze_glance_count
            return False, False
        next_count = locked.gaze_glance_count + 1
        completed = next_count >= threshold
        locked.gaze_glance_count = 0 if completed else next_count
        locked.gaze_glance_last_frame_hash = frame_hash
        locked.save(update_fields=['gaze_glance_count', 'gaze_glance_last_frame_hash', 'updated_at'])
        submission.gaze_glance_count = locked.gaze_glance_count
        return True, completed


def _gaze_strike_counts(submission, force_refresh: bool = False):
    """Return gaze strike counts, using an in-memory cache to avoid a DB query
    on every 100ms polling frame. Cache is invalidated whenever a strike is logged."""
    key = _gaze_pending_key(submission)
    if not force_refresh and key in _GAZE_STRIKE_CACHE:
        return _GAZE_STRIKE_CACHE[key]
    qs = ExamProctoringEvent.objects.filter(
        submission=submission,
        attempt_number=submission.attempt_count,
    )
    counts = {
        'gaze_violation_count': qs.filter(
            event_type=ExamProctoringEvent.EVENT_GAZE_VIOLATION,
        ).count(),
        'gaze_no_face_count': qs.filter(
            event_type=ExamProctoringEvent.EVENT_GAZE_NO_FACE,
        ).count(),
    }
    _GAZE_STRIKE_CACHE[key] = counts
    return counts


def _bulk_gaze_strike_counts(submissions):
    """Load current-attempt gaze and gadget flag counts in one query."""
    submissions = list(submissions)
    attempts = {submission.id: submission.attempt_count for submission in submissions}
    counts = {
        submission.id: {
            'gaze_violation_count': 0,
            'gaze_no_face_count': 0,
            'gadget_detection_count': 0,
        }
        for submission in submissions
    }
    if not attempts:
        return counts

    rows = (
        ExamProctoringEvent.objects.filter(
            submission_id__in=attempts,
            event_type__in=(
                ExamProctoringEvent.EVENT_GAZE_VIOLATION,
                ExamProctoringEvent.EVENT_GAZE_NO_FACE,
                ExamProctoringEvent.EVENT_GADGET_DETECTED,
            ),
        )
        .values('submission_id', 'attempt_number', 'event_type')
        .annotate(total=Count('id'))
    )
    for row in rows:
        submission_id = row['submission_id']
        if row['attempt_number'] != attempts.get(submission_id):
            continue
        key = {
            ExamProctoringEvent.EVENT_GAZE_VIOLATION: 'gaze_violation_count',
            ExamProctoringEvent.EVENT_GAZE_NO_FACE: 'gaze_no_face_count',
            ExamProctoringEvent.EVENT_GADGET_DETECTED: 'gadget_detection_count',
        }[row['event_type']]
        counts[submission_id][key] = row['total']
        _GAZE_STRIKE_CACHE[(submission_id, row['attempt_number'])] = counts[submission_id]
    return counts


def _clear_proctoring_for_attempt(submission):
    """Remove logs/evidence/reports when a student starts a fresh attempt."""
    attempt = submission.attempt_count
    ExamProctoringEvent.objects.filter(submission=submission, attempt_number=attempt).delete()
    ExamProctoringEvidence.objects.filter(submission=submission, attempt_number=attempt).delete()
    ExamIntegrityReport.objects.filter(submission=submission, attempt_number=attempt).delete()
    # Clear strike count cache for this attempt
    _GAZE_STRIKE_CACHE.pop((submission.pk, attempt), None)
    _GAZE_GLANCE_EPISODES.pop((submission.pk, attempt), None)
    _GADGET_DETECTION_STATE.pop((submission.pk, attempt), None)


def _purge_exam_set_student_records(exam_set):
    """Delete every student-facing record tied to an exam before the exam itself.

    Covers submissions, answers, proctoring events/evidence, integrity reports,
    and in-memory strike caches so Exam Progress stays clean after quiz deletion.
    """
    submissions = list(ExamSubmission.objects.filter(exam_set=exam_set))
    submission_ids = {submission.pk for submission in submissions}

    if submission_ids:
        for cache in (
            _GAZE_STRIKE_CACHE,
            _GAZE_LAST_LOGGED,
            _GAZE_PENDING_STRIKES,
            _GAZE_NO_FACE_ABSENCE,
            _GAZE_LAST_SUSPICIOUS,
            _GAZE_GLANCE_EPISODES,
            _GADGET_DETECTION_STATE,
        ):
            for key in list(cache.keys()):
                if key and key[0] in submission_ids:
                    cache.pop(key, None)

        for evidence in ExamProctoringEvidence.objects.filter(
            submission_id__in=submission_ids,
        ).iterator():
            if evidence.image:
                evidence.image.delete(save=False)

        for submission in submissions:
            if submission.latest_snapshot:
                submission.latest_snapshot.delete(save=False)

        ExamIntegrityReport.objects.filter(submission_id__in=submission_ids).delete()
        ExamProctoringEvidence.objects.filter(submission_id__in=submission_ids).delete()
        ExamProctoringEvent.objects.filter(submission_id__in=submission_ids).delete()
        ExamSubmission.objects.filter(pk__in=submission_ids).delete()

    StudentAnswer.objects.filter(exam_set=exam_set).delete()


def _log_proctoring_event(submission, event_type, *, severity=None, message='', source='', metadata=None):
    severity = severity or (
        ExamProctoringEvent.SEVERITY_CRITICAL
        if event_type in (
            ExamProctoringEvent.EVENT_EXAM_TERMINATED,
            ExamProctoringEvent.EVENT_TAB_SWITCH,
        )
        else ExamProctoringEvent.SEVERITY_WARNING
        if event_type in PROCTORING_EVENT_PENALTIES
        else ExamProctoringEvent.SEVERITY_INFO
    )
    safe_metadata = copy.deepcopy(metadata) if metadata else {}
    event = ExamProctoringEvent.objects.create(
        submission=submission,
        attempt_number=submission.attempt_count,
        event_type=event_type,
        severity=severity,
        message=message,
        source=source,
        metadata=safe_metadata,
    )
    if event_type in (
        ExamProctoringEvent.EVENT_GAZE_VIOLATION,
        ExamProctoringEvent.EVENT_GAZE_NO_FACE,
    ):
        _GAZE_STRIKE_CACHE.pop(_gaze_pending_key(submission), None)
    return event


def _resolve_forced_gaze_label(forced_label: str, classes: list[str]) -> str:
    """Map a client-supplied gaze label onto a tracker class name."""
    raw = (forced_label or '').strip()
    if not raw or not classes:
        return ''
    if raw in classes:
        return raw
    raw_l = raw.lower()
    for name in classes:
        if name.lower() == raw_l:
            return name

    def _direction(label: str) -> str:
        l = label.lower()
        if 'left' in l and 'right' not in l:
            return 'left'
        if 'right' in l and 'left' not in l:
            return 'right'
        if 'above' in l:
            return 'above'
        if 'below' in l:
            return 'below'
        return ''

    wanted = _direction(raw)
    if not wanted:
        return ''
    for name in classes:
        if _direction(name) == wanted:
            return name
    return ''


def _submission_snapshot_url(submission, request):
    """Authenticated API URL with a cache-buster for the instructor live view."""
    if not submission.latest_snapshot:
        return None
    url = request.build_absolute_uri(
        f'/api/instructor/subjects/{submission.exam_set.subject_id}'
        f'/exam-sets/{submission.exam_set_id}/submissions/{submission.pk}/snapshot/'
    )
    version = int(submission.updated_at.timestamp()) if submission.updated_at else int(timezone.now().timestamp())
    sep = '&' if '?' in url else '?'
    return f'{url}{sep}v={version}'


def _gaze_event_metadata(result, **extra) -> dict:
    """JSON-safe metadata for gaze events (never the full API payload)."""
    meta = {
        'label': result.label,
        'confidence': round(float(result.confidence), 4),
        'face_detected': result.face_detected,
        'is_normal': result.is_normal,
        'is_suspicious': result.is_suspicious,
        'probabilities': {
            k: round(float(v), 4) for k, v in (result.probabilities or {}).items()
        },
    }
    for key, value in extra.items():
        if key in ('logged_event', 'evidence'):
            continue
        if isinstance(value, (int, float, str, bool)) or value is None:
            meta[key] = value
        elif isinstance(value, dict):
            meta[key] = copy.deepcopy(value)
    return meta


def _compute_integrity_score(submission):
    events = ExamProctoringEvent.objects.filter(
        submission=submission,
        attempt_number=submission.attempt_count,
    )
    score = Decimal('100')
    counts = {}
    for event in events:
        counts[event.event_type] = counts.get(event.event_type, 0) + 1
        penalty = PROCTORING_EVENT_PENALTIES.get(event.event_type, 0)
        if penalty:
            score -= Decimal(penalty)

    if submission.terminated:
        score = min(score, Decimal('35'))

    # Also penalize tab_switches field if higher than logged events
    tab_events = counts.get(ExamProctoringEvent.EVENT_TAB_SWITCH, 0)
    extra_tabs = max(0, submission.tab_switches - tab_events)
    if extra_tabs:
        score -= Decimal(12 * extra_tabs)

    score = max(Decimal('0'), min(Decimal('100'), score))
    return score.quantize(Decimal('0.01')), counts


def _build_integrity_report(submission):
    score, counts = _compute_integrity_score(submission)
    events = ExamProctoringEvent.objects.filter(
        submission=submission,
        attempt_number=submission.attempt_count,
    )
    evidence_qs = ExamProctoringEvidence.objects.filter(
        submission=submission,
        attempt_number=submission.attempt_count,
    )
    warning_count = events.filter(severity=ExamProctoringEvent.SEVERITY_WARNING).count()
    critical_count = events.filter(severity=ExamProctoringEvent.SEVERITY_CRITICAL).count()
    tab_switch_count = counts.get(ExamProctoringEvent.EVENT_TAB_SWITCH, submission.tab_switches)
    split_screen_count = counts.get(ExamProctoringEvent.EVENT_SPLIT_SCREEN, 0)
    extended_monitor_count = counts.get(ExamProctoringEvent.EVENT_EXTENDED_MONITOR, 0)
    gaze_violations = counts.get(ExamProctoringEvent.EVENT_GAZE_VIOLATION, 0)
    gaze_no_face = counts.get(ExamProctoringEvent.EVENT_GAZE_NO_FACE, 0)
    gadget_detections = counts.get(ExamProctoringEvent.EVENT_GADGET_DETECTED, 0)

    narrative_parts = [
        f'Integrity score: {score}%.',
        f'Total logged events: {events.count()}.',
        f'Warnings: {warning_count}, critical: {critical_count}.',
        f'Tab switches: {tab_switch_count}.',
        f'Split-screen or window-resize warnings: {split_screen_count}.',
        f'Extended-monitor warnings: {extended_monitor_count}.',
        f'Gaze away from screen: {gaze_violations}.',
        f'Face not visible (gaze): {gaze_no_face}.',
        f'Confirmed prohibited gadgets: {gadget_detections}.',
        f'Screenshots/evidence captured: {evidence_qs.count()}.',
    ]
    if submission.terminated:
        narrative_parts.append('Exam was auto-terminated due to proctoring violations.')

    summary = {
        'gaze_model_code': submission.gaze_model_code,
        'event_counts': counts,
        'terminated': submission.terminated,
        'tab_switches': submission.tab_switches,
        'split_screen_count': split_screen_count,
        'extended_monitor_count': extended_monitor_count,
        'gaze_violation_count': gaze_violations,
        'gaze_no_face_count': gaze_no_face,
        'gadget_detection_count': gadget_detections,
    }

    report, _ = ExamIntegrityReport.objects.update_or_create(
        submission=submission,
        attempt_number=submission.attempt_count,
        defaults={
            'integrity_score': score,
            'event_count': events.count(),
            'warning_count': warning_count,
            'critical_count': critical_count,
            'evidence_count': evidence_qs.count(),
            'tab_switch_count': tab_switch_count,
            'gaze_violation_count': gaze_violations,
            'gaze_no_face_count': gaze_no_face,
            'summary': summary,
            'narrative': ' '.join(narrative_parts),
        },
    )
    submission.integrity_score = score
    submission.save(update_fields=['integrity_score'])
    return report


def _serialize_proctoring_event(event):
    return {
        'id': event.id,
        'event_type': event.event_type,
        'severity': event.severity,
        'message': event.message,
        'source': event.source,
        'metadata': event.metadata,
        'created_at': event.created_at,
    }


def _serialize_proctoring_evidence(evidence, request=None):
    url = ''
    if evidence.image:
        try:
            url = evidence.image.url or ''
        except Exception:
            url = ''
    if url and request and url.startswith('/'):
        url = request.build_absolute_uri(url)
    return {
        'id': evidence.id,
        'evidence_type': evidence.evidence_type,
        'image_url': url,
        'caption': evidence.caption,
        'created_at': evidence.created_at,
        'event_id': evidence.event_id,
    }


@api_view(['POST'])
@permission_classes([AllowAny])
def admin_login(request):
    username = request.data.get('username', '')
    password = request.data.get('password', '')

    if (
        not isinstance(username, str)
        or not isinstance(password, str)
        or not username.strip()
        or not password
    ):
        return Response({'error': 'Invalid admin credentials.'}, status=status.HTTP_401_UNAUTHORIZED)

    admin_user = authenticate(request, username=username.strip(), password=password)
    if not admin_user or not admin_user.is_staff or not admin_user.is_superuser:
        return Response({'error': 'Invalid admin credentials.'}, status=status.HTTP_401_UNAUTHORIZED)

    profile, _ = UserProfile.objects.get_or_create(
        user=admin_user,
        defaults={'role': 'admin', 'is_enrolled': False},
    )
    if profile.role != 'admin':
        profile.role = 'admin'
        profile.save(update_fields=['role'])

    refresh = RefreshToken.for_user(admin_user)
    return Response(
        {
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh),
            'user': {
                'role': 'admin',
                'username': admin_user.username,
                'email': admin_user.email or '',
            },
        },
        status=status.HTTP_200_OK,
    )


def _is_admin(user):
    return bool(user and user.is_authenticated and user.is_superuser)


def _valid_institute(value):
    return isinstance(value, str) and value in dict(UserProfile.INSTITUTE_CHOICES)


def _course_instructors(instructor_ids, category):
    if not isinstance(instructor_ids, list) or not instructor_ids or any(
        isinstance(value, bool) or not str(value).isdigit() for value in instructor_ids
    ):
        return None
    ids = [int(value) for value in instructor_ids]
    if len(set(ids)) != len(ids):
        return None
    by_id = {
        user.id: user for user in User.objects.filter(
            id__in=ids, is_active=True, is_staff=True, is_superuser=False,
            profile__role='instructor',
        ).select_related('profile')
    }
    instructors = [by_id.get(user_id) for user_id in ids]
    if any(user is None or (category != Subject.CATEGORY_MINOR and user.profile.institute != category)
           for user in instructors):
        return None
    return instructors


def _serialize_admin_course(subject):
    instructors = [subject.instructor, *subject.additional_instructors.all()]
    return {
        'id': subject.id,
        'name': subject.name,
        'code': subject.code,
        'category': subject.category,
        'instructor_id': subject.instructor_id,
        'instructor_name': subject.instructor.get_full_name() or subject.instructor.email,
        'instructor_email': subject.instructor.email,
        'instructor_ids': [instructor.id for instructor in instructors],
        'instructor_names': [instructor.get_full_name() or instructor.email for instructor in instructors],
        'student_count': getattr(subject, 'student_count', 0),
        'exam_count': getattr(subject, 'exam_count', 0),
    }


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def admin_courses(request):
    """Admin: browse institute and minor courses, or create one for an instructor."""
    if not _is_admin(request.user):
        return Response({'error': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        courses = Subject.objects.select_related('instructor').prefetch_related('additional_instructors').annotate(
            student_count=Count('student_sets__students__email', distinct=True),
            exam_count=Count('exam_sets', distinct=True),
        ).order_by('category', 'name', 'code')
        return Response({'courses': [_serialize_admin_course(course) for course in courses]})

    name = request.data.get('name')
    code = request.data.get('code')
    category = request.data.get('category')
    if not isinstance(name, str) or not isinstance(code, str) or not name.strip() or not code.strip():
        return Response({'error': 'Course name and code are required.'}, status=status.HTTP_400_BAD_REQUEST)
    if len(name.strip()) > 200 or len(code.strip()) > 50:
        return Response({'error': 'Course name or code is too long.'}, status=status.HTTP_400_BAD_REQUEST)
    if category not in dict(Subject.CATEGORY_CHOICES):
        return Response({'error': 'Choose an institute or Minor courses.'}, status=status.HTTP_400_BAD_REQUEST)
    instructors = _course_instructors(request.data.get('instructor_ids'), category)
    if instructors is None:
        return Response({'error': 'Choose one or more active instructors in this institute. Minor courses may use instructors from any institute.'}, status=status.HTTP_400_BAD_REQUEST)
    code = code.strip().upper()
    if Subject.objects.filter(code__iexact=code).filter(
        Q(instructor__in=instructors) | Q(additional_instructors__in=instructors)
    ).exists():
        return Response({'error': 'An assigned instructor already has a course with that code.'}, status=status.HTTP_409_CONFLICT)
    with transaction.atomic():
        subject = Subject.objects.create(
            instructor=instructors[0], name=name.strip(), code=code, category=category,
        )
        subject.additional_instructors.set(instructors[1:])
    return Response(_serialize_admin_course(subject), status=status.HTTP_201_CREATED)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def admin_course_detail(request, subject_id):
    """Admin: reclassify or reassign a course while preserving its exams and rosters."""
    if not _is_admin(request.user):
        return Response({'error': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)
    subject = Subject.objects.select_related('instructor').prefetch_related('additional_instructors').annotate(
        student_count=Count('student_sets__students__email', distinct=True),
        exam_count=Count('exam_sets', distinct=True),
    ).filter(pk=subject_id).first()
    if subject is None:
        return Response({'error': 'Course not found.'}, status=status.HTTP_404_NOT_FOUND)
    if 'category' not in request.data and 'instructor_ids' not in request.data:
        return Response({'error': 'Choose a category or instructors to update.'}, status=status.HTTP_400_BAD_REQUEST)
    category = request.data.get('category', subject.category)
    if category not in dict(Subject.CATEGORY_CHOICES):
        return Response({'error': 'Choose an institute or Minor courses.'}, status=status.HTTP_400_BAD_REQUEST)
    current_ids = [subject.instructor_id, *subject.additional_instructors.values_list('id', flat=True)]
    instructors = _course_instructors(request.data.get('instructor_ids', current_ids), category)
    if instructors is None:
        return Response({'error': 'Choose one or more active instructors in this institute. Minor courses may use instructors from any institute.'}, status=status.HTTP_400_BAD_REQUEST)
    if Subject.objects.filter(code__iexact=subject.code).exclude(pk=subject.pk).filter(
        Q(instructor__in=instructors) | Q(additional_instructors__in=instructors)
    ).exists():
        return Response({'error': 'An assigned instructor already has a course with that code.'}, status=status.HTTP_409_CONFLICT)
    previous_instructor_id = subject.instructor_id
    with transaction.atomic():
        subject.category = category
        subject.instructor = instructors[0]
        subject.save(update_fields=['category', 'instructor'])
        subject.additional_instructors.set(instructors[1:])
        removed_ids = set(current_ids) - {instructor.id for instructor in instructors}
        if removed_ids:
            subject.archived_by.remove(*removed_ids)
        if previous_instructor_id != instructors[0].id:
            subject.student_sets.update(created_by=instructors[0])
    return Response(_serialize_admin_course(subject))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_analytics(request):
    """Campus-wide exam analytics from recorded attempts and proctoring events."""
    if not _is_admin(request.user):
        return Response({'error': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

    from .gaze_service import GAZE_MODEL_NAMES, selected_gaze_model_code
    model_scores = {code: [] for code in GAZE_MODEL_NAMES}

    institute_names = dict(UserProfile.INSTITUTE_CHOICES)
    institute_by_email = {
        email.lower(): institute
        for email, institute in UserProfile.objects.filter(role='student').values_list('user__email', 'institute')
        if email
    }
    reports = ExamIntegrityReport.objects.select_related('submission').all()
    institute_scores = {code: [] for code in institute_names}
    score_total = Decimal('0')
    flagged_attempts = 0
    terminated_attempts = 0
    report_count = 0
    for report in reports.iterator():
        report_count += 1
        score_total += report.integrity_score
        model_code = (report.summary or {}).get('gaze_model_code')
        if model_code in model_scores:
            model_scores[model_code].append(report.integrity_score)
        if report.integrity_score < 100:
            flagged_attempts += 1
        if (report.summary or {}).get('terminated'):
            terminated_attempts += 1
        institute = institute_by_email.get(report.submission.student_email.lower())
        if institute in institute_scores:
            institute_scores[institute].append(report.integrity_score)

    institute_rows = [
        {
            'code': code,
            'name': name,
            'average_integrity': round(float(sum(institute_scores[code]) / len(institute_scores[code])), 1)
                if institute_scores[code] else None,
            'attempts': len(institute_scores[code]),
        }
        for code, name in institute_names.items()
    ]
    scored_institutes = [row for row in institute_rows if row['attempts']]
    lowest_institute = min(scored_institutes, key=lambda row: row['average_integrity']) if scored_institutes else None
    gaze_model_rows = [
        {
            'code': code,
            'name': name,
            'average_integrity': round(float(sum(model_scores[code]) / len(model_scores[code])), 1)
                if model_scores[code] else None,
            'attempts': len(model_scores[code]),
        }
        for code, name in GAZE_MODEL_NAMES.items()
    ]

    violation_types = {
        key: label for key, label in ExamProctoringEvent.EVENT_TYPES
        if key in PROCTORING_EVENT_PENALTIES and key not in {
            ExamProctoringEvent.EVENT_WINDOW_BLUR,
            ExamProctoringEvent.EVENT_EXAM_TERMINATED,
        }
    }
    violation_counts = dict(
        ExamProctoringEvent.objects.filter(event_type__in=violation_types)
        .values('event_type').annotate(total=Count('id'))
        .values_list('event_type', 'total')
    )
    violations = sorted(
        ({'key': key, 'label': label, 'count': violation_counts.get(key, 0)}
         for key, label in violation_types.items()),
        key=lambda row: (-row['count'], row['label']),
    )

    device_counts = {}
    gadget_events = ExamProctoringEvent.objects.filter(
        event_type=ExamProctoringEvent.EVENT_GADGET_DETECTED,
    ).values_list('metadata', flat=True)
    for metadata in gadget_events.iterator():
        detections = metadata.get('detections', []) if isinstance(metadata, dict) else []
        labels = {
            item['label'].strip().lower()
            for item in detections
            if isinstance(item, dict) and isinstance(item.get('label'), str) and item['label'].strip()
        } if isinstance(detections, list) else set()
        for label in labels or {'Unspecified device'}:
            device_counts[label] = device_counts.get(label, 0) + 1
    devices = [
        {'label': label.capitalize(), 'count': count}
        for label, count in sorted(device_counts.items(), key=lambda item: (-item[1], item[0]))
    ]

    return Response({
        'summary': {
            'completed_attempts': report_count,
            'average_integrity': round(float(score_total / report_count), 1) if report_count else None,
            'flagged_attempts': flagged_attempts,
            'terminated_attempts': terminated_attempts,
            'recorded_violations': sum(violation_counts.values()),
        },
        'violations': violations,
        'devices': devices,
        'institutes': institute_rows,
        'lowest_institute': lowest_institute,
        'gaze_models': gaze_model_rows,
        'active_gaze_model': selected_gaze_model_code(),
        'unattributed_attempts': report_count - sum(row['attempts'] for row in gaze_model_rows),
    })


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def admin_gaze_model(request):
    """Admin: select one compatible gaze model for all exam inference."""
    if not _is_admin(request.user):
        return Response({'error': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)
    from .gaze_service import (
        GAZE_MODEL_FILES, gaze_model_options, prepare_gaze_model,
        selected_gaze_model_code, set_selected_gaze_model_code,
    )
    if request.method == 'PATCH':
        code = request.data.get('model_code')
        if code not in GAZE_MODEL_FILES:
            return Response({'error': 'Choose a supported gaze model.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            prepare_gaze_model(code)
        except (ValueError, OSError, RuntimeError, KeyError) as exc:
            return Response({'error': str(exc)}, status=status.HTTP_409_CONFLICT)
        GazeModelSelection.objects.update_or_create(pk=1, defaults={'model_code': code})
        set_selected_gaze_model_code(code)
    return Response({
        'selected_model': selected_gaze_model_code(),
        'models': gaze_model_options(),
    })


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def admin_instructors(request):
    """Admin: list all registered instructors, or register a new instructor by email."""
    if not _is_admin(request.user):
        return Response({'error': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        instructors = User.objects.filter(
            Q(is_staff=True) | Q(profile__role='instructor'), is_superuser=False,
        ).select_related('profile').distinct().order_by('email')
        data = []
        for u in instructors:
            data.append({
                'id': u.id,
                'username': u.username,
                'email': u.email,
                'first_name': u.first_name,
                'last_name': u.last_name,
                'full_name': u.get_full_name() or u.username,
                'is_active': u.is_active,
                'institute': u.profile.institute if hasattr(u, 'profile') else '',
            })
        return Response({'instructors': data}, status=status.HTTP_200_OK)

    email = (request.data.get('email') or '').strip().lower()
    first_name = (request.data.get('first_name') or '').strip()
    last_name = (request.data.get('last_name') or '').strip()
    institute = request.data.get('institute')

    if not email:
        return Response({'error': 'Email is required.'}, status=status.HTTP_400_BAD_REQUEST)
    if not _valid_institute(institute):
        return Response({'error': 'Choose a valid institute.'}, status=status.HTTP_400_BAD_REQUEST)
    if not email.endswith(f"@{settings.ALLOWED_SCHOOL_DOMAIN}"):
        return Response(
            {'error': f"Only @{settings.ALLOWED_SCHOOL_DOMAIN} emails are allowed."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user, created = User.objects.get_or_create(
        username=email,
        defaults={
            'email': email,
            'first_name': first_name,
            'last_name': last_name,
            'is_staff': True,
            'is_superuser': False,
        },
    )
    if not created:
        return Response(
            {'error': 'This account already exists. Use the instructors list to manage access.'},
            status=status.HTTP_409_CONFLICT,
        )

    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={'role': 'instructor', 'is_enrolled': False, 'institute': institute},
    )
    if profile.role != 'instructor':
        profile.role = 'instructor'
        profile.save(update_fields=['role'])

    return Response(
        {
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'full_name': user.get_full_name() or user.username,
            'created': created,
            'is_active': user.is_active,
            'institute': profile.institute,
        },
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


@api_view(['PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def admin_instructor_detail(request, instructor_id):
    """Admin: manage or remove an instructor account."""
    if not _is_admin(request.user):
        return Response({'error': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

    instructor = User.objects.filter(
        Q(is_staff=True) | Q(profile__role='instructor'), id=instructor_id, is_superuser=False,
    ).first()
    if not instructor:
        return Response({'error': 'Instructor not found.'}, status=status.HTTP_404_NOT_FOUND)
    if request.method == 'DELETE':
        with transaction.atomic():
            if Subject.objects.filter(Q(instructor=instructor) | Q(additional_instructors=instructor)).exists():
                return Response(
                    {'error': 'Reassign this instructor’s courses before deleting their account.'},
                    status=status.HTTP_409_CONFLICT,
                )
            # Standalone rosters may still reference their creator. Keep those
            # rosters and enrollments when the instructor account is removed.
            StudentSet.objects.filter(created_by=instructor).update(created_by=None)
            instructor.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    if request.data.get('action') == 'set_email':
        email = str(request.data.get('email') or '').strip().lower()
        try:
            validate_email(email)
        except ValidationError:
            return Response({'error': 'Enter a valid school email address.'}, status=status.HTTP_400_BAD_REQUEST)
        if not email.endswith(f"@{settings.ALLOWED_SCHOOL_DOMAIN}"):
            return Response(
                {'error': f"Only @{settings.ALLOWED_SCHOOL_DOMAIN} emails are allowed."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if User.objects.filter(Q(username__iexact=email) | Q(email__iexact=email)).exclude(pk=instructor.pk).exists():
            return Response({'error': 'This email is already used by another account.'}, status=status.HTTP_409_CONFLICT)
        instructor.username = email
        instructor.email = email
        try:
            instructor.save(update_fields=['username', 'email'])
        except IntegrityError:
            return Response({'error': 'This email is already used by another account.'}, status=status.HTTP_409_CONFLICT)
        return Response({'id': instructor.id, 'email': email, 'username': email})
    if request.data.get('action') == 'set_institute':
        institute = request.data.get('institute')
        if not _valid_institute(institute):
            return Response({'error': 'Choose a valid institute.'}, status=status.HTTP_400_BAD_REQUEST)
        if Subject.objects.filter(Q(instructor=instructor) | Q(additional_instructors=instructor)).exclude(category__in=['', Subject.CATEGORY_MINOR, institute]).exists():
            return Response(
                {'error': 'Reassign this instructor’s institute courses before changing their institute.'},
                status=status.HTTP_409_CONFLICT,
            )
        profile, _ = UserProfile.objects.get_or_create(
            user=instructor, defaults={'role': 'instructor', 'is_enrolled': False},
        )
        profile.institute = institute
        profile.save(update_fields=['institute'])
        return Response({'id': instructor.id, 'institute': institute})
    active = request.data.get('is_active')
    if not isinstance(active, bool):
        return Response({'error': 'is_active must be a boolean.'}, status=status.HTTP_400_BAD_REQUEST)
    profile, _ = UserProfile.objects.get_or_create(
        user=instructor, defaults={'role': 'instructor', 'is_enrolled': False},
    )
    if profile.role != 'instructor':
        profile.role = 'instructor'
        profile.save(update_fields=['role'])
    instructor.is_active = active
    instructor.is_staff = active
    instructor.save(update_fields=['is_active', 'is_staff'])
    return Response({'id': instructor.id, 'is_active': active})


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def admin_students(request):
    """Admin: list all formally enrolled students, or formally enroll a new student."""
    if not _is_admin(request.user):
        return Response({'error': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        # Return all users with student profile
        students = User.objects.filter(
            profile__role='student'
        ).select_related('profile').order_by('email')
        data = []
        for u in students:
            p = getattr(u, 'profile', None)
            face_photo_url = None
            face_pending_url = None
            if p:
                if p.face_photo and p.id_verified_at:
                    face_photo_url = request.build_absolute_uri(p.face_photo.url)
                if p.face_pending_photo:
                    face_pending_url = request.build_absolute_uri(p.face_pending_photo.url)
            data.append({
                'id': u.id,
                'email': u.email,
                'first_name': u.first_name,
                'last_name': u.last_name,
                'full_name': u.get_full_name() or u.email,
                'is_enrolled': p and p.is_enrolled,
                'institute': p.institute if p else '',
                'face_status': _effective_face_status(p),
                'face_reupload_allowed': p.face_reupload_allowed if p else False,
                'face_photo_url': face_photo_url,
                'face_pending_photo_url': face_pending_url,
            })
        return Response({'students': data}, status=status.HTTP_200_OK)

    email = (request.data.get('email') or '').strip().lower()
    first_name = (request.data.get('first_name') or '').strip()
    last_name = (request.data.get('last_name') or '').strip()
    institute = request.data.get('institute')

    if not email:
        return Response({'error': 'Email is required.'}, status=status.HTTP_400_BAD_REQUEST)
    if not _valid_institute(institute):
        return Response({'error': 'Choose a valid institute.'}, status=status.HTTP_400_BAD_REQUEST)
    if not email.endswith(f"@{settings.ALLOWED_SCHOOL_DOMAIN}"):
        return Response(
            {'error': f"Only @{settings.ALLOWED_SCHOOL_DOMAIN} emails are allowed."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Create or update the user account for this student
    user, created = User.objects.get_or_create(
        username=email,
        defaults={
            'email': email,
            'first_name': first_name,
            'last_name': last_name,
            'is_staff': False,
        },
    )
    if not created and (
        user.is_staff or user.is_superuser
        or UserProfile.objects.filter(user=user, role='instructor').exists()
    ):
        return Response(
            {'error': 'This email belongs to an instructor account.'},
            status=status.HTTP_409_CONFLICT,
        )
    name_changed = not created and (
        (bool(first_name) and first_name != user.first_name)
        or (bool(last_name) and last_name != user.last_name)
    )
    if not created:
        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name
        user.save()

    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={'role': 'student', 'is_enrolled': True, 'institute': institute},
    )
    profile.is_enrolled = True
    profile.institute = institute
    if name_changed:
        profile.id_verified_at = None
        profile.face_status = UserProfile.FACE_STATUS_NONE
        profile.face_encoding = None
    if profile.role != 'student':
        profile.role = 'student'
    with transaction.atomic():
        profile.save(update_fields=['role', 'is_enrolled', 'institute', 'id_verified_at', 'face_status', 'face_encoding'])
        if not user.is_active:
            user.is_active = True
            user.save(update_fields=['is_active'])

    return Response(
        {
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'full_name': user.get_full_name() or user.email,
            'is_enrolled': True,
            'institute': profile.institute,
            'created': created,
        },
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def admin_student_detail(request, student_id):
    """Admin: manage a student account, access, and identity review."""
    if not _is_admin(request.user):
        return Response({'error': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

    student = User.objects.filter(id=student_id, is_staff=False).select_related('profile').first()
    if not student or not hasattr(student, 'profile') or student.profile.role != 'student':
        return Response({'error': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)

    profile = student.profile

    if request.method == 'DELETE':
        email = student.email
        stored_photos = [
            (field.storage, field.name)
            for field in (profile.face_photo, profile.face_pending_photo, profile.custom_photo)
            if field and field.name
        ]
        with transaction.atomic():
            EnrolledStudent.objects.filter(email__iexact=email).delete()
            SubjectEnrollment.objects.filter(email__iexact=email).delete()
            student.delete()
            # Exam submissions and evidence are retained for integrity review.
            def remove_identity_photos():
                for storage, name in stored_photos:
                    try:
                        storage.delete(name)
                    except Exception:
                        pass
            transaction.on_commit(remove_identity_photos)
        return Response(status=status.HTTP_204_NO_CONTENT)

    if request.method == 'GET':
        face_photo_url = request.build_absolute_uri(profile.face_photo.url) if profile.face_photo and profile.id_verified_at else None
        face_pending_url = request.build_absolute_uri(profile.face_pending_photo.url) if profile.face_pending_photo else None
        return Response({
            'id': student.id,
            'email': student.email,
            'full_name': student.get_full_name() or student.email,
            'institute': profile.institute,
            'face_status': _effective_face_status(profile),
            'face_reupload_allowed': profile.face_reupload_allowed,
            'face_photo_url': face_photo_url,
            'face_pending_photo_url': face_pending_url,
        })

    if request.method == 'PATCH':
        action = request.data.get('action')

        if action == 'set_institute':
            institute = request.data.get('institute')
            if not _valid_institute(institute):
                return Response({'error': 'Choose a valid institute.'}, status=status.HTTP_400_BAD_REQUEST)
            profile.institute = institute
            profile.save(update_fields=['institute'])
            return Response({'id': student.id, 'institute': institute})

        if action == 'approve_face':
            return Response({'error': 'Students must upload a DNSC student ID for automatic verification.'}, status=status.HTTP_400_BAD_REQUEST)


        elif action == 'reject_face':
            if profile.face_pending_photo:
                try:
                    profile.face_pending_photo.delete(save=False)
                except Exception:
                    pass
            profile.face_pending_photo = None
            profile.face_encoding = None  # clear cached encoding from upload
            profile.face_status = UserProfile.FACE_STATUS_NONE
            profile.save(update_fields=['face_pending_photo', 'face_encoding', 'face_status'])
            return Response({'message': 'Pending face photo rejected.', 'face_status': profile.face_status})

        elif action == 'set_enrollment':
            enrolled = request.data.get('is_enrolled')
            if not isinstance(enrolled, bool):
                return Response({'error': 'is_enrolled must be a boolean.'}, status=status.HTTP_400_BAD_REQUEST)
            profile.is_enrolled = enrolled
            student.is_active = enrolled
            with transaction.atomic():
                profile.save(update_fields=['is_enrolled'])
                student.save(update_fields=['is_active'])
            return Response({'id': student.id, 'is_enrolled': enrolled})

        elif action == 'toggle_reupload':
            # Flip the reupload flag. If enabling, reset status so student can submit fresh.
            profile.face_reupload_allowed = not profile.face_reupload_allowed
            profile.face_status = (
                UserProfile.FACE_STATUS_NONE if profile.face_reupload_allowed or not profile.face_photo or not profile.id_verified_at
                else UserProfile.FACE_STATUS_APPROVED
            )
            profile.save(update_fields=['face_reupload_allowed', 'face_status'])
            return Response({
                'message': 'Re-upload permission updated.',
                'face_reupload_allowed': profile.face_reupload_allowed,
                'face_status': profile.face_status,
            })

        return Response({'error': 'Unknown student update action.'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def enrolled_students(request):
    if not _is_instructor(request.user):
        return Response({'error': 'Instructor access required.'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        qs = EnrolledStudent.objects.filter(
            Q(student_set__created_by=request.user, student_set__subject__isnull=True)
            | Q(student_set__subject__instructor=request.user)
            | Q(student_set__subject__additional_instructors=request.user)
        ).distinct().select_related(
            'student_set'
        ).order_by('student_set_id', 'email')
        student_set_id = request.query_params.get('student_set_id')
        if student_set_id:
            qs = qs.filter(student_set_id=student_set_id)
        students = [
            {
                'id': r.id,
                'email': r.email,
                'created_at': r.created_at,
                'student_set_id': r.student_set_id,
                'student_set_name': r.student_set.name if r.student_set else None,
            }
            for r in qs
        ]
        return Response({'students': students}, status=status.HTTP_200_OK)

    email = (request.data.get('email') or '').strip().lower()
    student_set_id = request.data.get('student_set_id')
    if not email:
        return Response({'error': 'Email required.'}, status=status.HTTP_400_BAD_REQUEST)
    if not student_set_id:
        return Response(
            {'error': 'student_set_id required. Create or select a student set first.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not email.endswith(f"@{settings.ALLOWED_SCHOOL_DOMAIN}"):
        return Response(
            {'error': f"Only @{settings.ALLOWED_SCHOOL_DOMAIN} emails are allowed."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    roster = StudentSet.objects.filter(
        Q(created_by=request.user, subject__isnull=True)
        | Q(subject__instructor=request.user)
        | Q(subject__additional_instructors=request.user),
        id=student_set_id,
    ).distinct().first()
    if not roster:
        return Response(
            {'error': 'Student set not found or you do not have access to it.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    if not UserProfile.objects.filter(user__email__iexact=email, role='student', is_enrolled=True).exists():
        return Response(
            {'error': 'This student has not been enrolled by the admin.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        student, existing = _enroll_student_in_set_once(email, roster)
    except IntegrityError:
        return Response(
            {'error': 'This email is already in this set.'},
            status=status.HTTP_409_CONFLICT,
        )
    if existing:
        message = (
            f'This student is already enrolled in this course through {existing.student_set.name}.'
            if roster.subject_id and existing.student_set_id != roster.id
            else 'This email is already in this set.'
        )
        return Response({'error': message}, status=status.HTTP_409_CONFLICT)

    _sync_profile_enrollment_for_email(email)

    return Response(
        {
            'id': student.id,
            'email': student.email,
            'created_at': student.created_at,
            'student_set_id': student.student_set_id,
            'student_set_name': roster.name,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bulk_enroll_students(request, set_id):
    if not _is_instructor(request.user):
        return Response({'error': 'Instructor access required.'}, status=status.HTTP_403_FORBIDDEN)

    roster = StudentSet.objects.filter(
        Q(created_by=request.user, subject__isnull=True)
        | Q(subject__instructor=request.user)
        | Q(subject__additional_instructors=request.user),
        id=set_id,
    ).distinct().first()
    if not roster:
        return Response(
            {'error': 'Student set not found or you do not have access to it.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    upload = request.FILES.get('file')
    source_rows = []
    if upload:
        if not upload.name.lower().endswith('.xlsx'):
            return Response(
                {'error': 'Only .xlsx Excel files are supported.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if upload.size > 5 * 1024 * 1024:
            return Response(
                {'error': 'The Excel file must be 5 MB or smaller.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            workbook = load_workbook(upload, read_only=True, data_only=True)
            worksheet = workbook.active
            if worksheet is None:
                raise ValueError('The Excel file does not contain a worksheet.')
            if worksheet.max_row > 5001:
                raise ValueError('The Excel file can contain at most 5,000 students.')
            rows = worksheet.iter_rows(values_only=True)
            headers = next(rows, None)
            if not headers:
                raise ValueError('The Excel file is empty.')

            normalized_headers = [
                re.sub(r'[^a-z]', '', str(value or '').strip().lower())
                for value in headers
            ]
            accepted_headers = {'email', 'emailaddress', 'studentemail', 'studentemailaddress'}
            email_column = next(
                (index for index, header in enumerate(normalized_headers) if header in accepted_headers),
                None,
            )
            if email_column is None:
                raise ValueError(
                    'No email column was found. Name the column "Email" or "Student Email".'
                )

            for row_number, row in enumerate(rows, start=2):
                value = row[email_column] if email_column < len(row) else None
                if value is None or not str(value).strip():
                    continue
                source_rows.append((row_number, str(value).strip().lower()))
                if len(source_rows) > 5000:
                    raise ValueError('The Excel file can contain at most 5,000 students.')
        except (InvalidFileException, BadZipFile, OSError, EOFError):
            return Response(
                {'error': 'The uploaded file is not a valid .xlsx workbook.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        finally:
            if 'workbook' in locals():
                workbook.close()

        lines = [email for _, email in source_rows]
    else:
        raw = request.data.get('emails')
        if isinstance(raw, list):
            lines = [str(x).strip().lower() for x in raw if str(x).strip()]
        else:
            lines = [
                part.strip().lower()
                for part in (raw or '').replace(',', '\n').splitlines()
                if part.strip()
            ]

    if not lines:
        return Response({'error': 'No emails provided.'}, status=status.HTTP_400_BAD_REQUEST)

    added = []
    skipped = []
    errors = []
    domain = f"@{settings.ALLOWED_SCHOOL_DOMAIN}"

    for index, line in enumerate(lines):
        email = line.strip().lower()
        row_number = source_rows[index][0] if source_rows else None
        if not email.endswith(domain):
            item = {'email': email, 'error': f'Not a {domain} address.'}
            if row_number:
                item['row'] = row_number
            errors.append(item)
            continue
        if not UserProfile.objects.filter(user__email__iexact=email, role='student', is_enrolled=True).exists():
            item = {'email': email, 'error': 'Not enrolled by admin.'}
            if row_number:
                item['row'] = row_number
            errors.append(item)
            continue
        try:
            s, existing = _enroll_student_in_set_once(email, roster)
            if existing:
                skipped.append(email)
                continue
            added.append({'id': s.id, 'email': s.email})
            _sync_profile_enrollment_for_email(email)
        except IntegrityError:
            skipped.append(email)
        except Exception as exc:
            item = {'email': email, 'error': str(exc)}
            if row_number:
                item['row'] = row_number
            errors.append(item)

    result = {'added': added, 'skipped_duplicates': skipped, 'errors': errors}
    if upload:
        result.update({'file_name': upload.name, 'rows_processed': len(lines)})
    return Response(result, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_enrolled_student(request, student_id):
    if not _is_instructor(request.user):
        return Response({'error': 'Instructor access required.'}, status=status.HTTP_403_FORBIDDEN)

    student = (
        EnrolledStudent.objects.select_related('student_set')
        .filter(id=student_id)
        .first()
    )
    if not student:
        return Response({'error': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)
    if student.student_set and student.student_set.created_by_id != request.user.id:
        return Response({'error': 'You cannot modify this enrollment.'}, status=status.HTTP_403_FORBIDDEN)
    email = student.email
    student.delete()
    _sync_profile_enrollment_for_email(email)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def student_sets(request):
    if not _is_instructor(request.user):
        return Response({'error': 'Instructor access required.'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        rows = (
            StudentSet.objects.filter(created_by=request.user, subject__isnull=True)
            .annotate(student_count=Count('students', distinct=True))
            .values('id', 'name', 'created_at', 'student_count')
        )
        return Response({'sets': list(rows)}, status=status.HTTP_200_OK)

    name = (request.data.get('name') or '').strip()
    if not name:
        return Response({'error': 'Set name is required.'}, status=status.HTTP_400_BAD_REQUEST)
    s = StudentSet.objects.create(name=name, created_by=request.user, subject=None)
    return Response(
        {'id': s.id, 'name': s.name, 'created_at': s.created_at, 'student_count': 0},
        status=status.HTTP_201_CREATED,
    )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def student_set_detail(request, set_id):
    if not _is_instructor(request.user):
        return Response({'error': 'Instructor access required.'}, status=status.HTTP_403_FORBIDDEN)

    roster = (
        StudentSet.objects.filter(id=set_id, created_by=request.user, subject__isnull=True)
        .prefetch_related('students')
        .first()
    )
    if not roster:
        return Response({'error': 'Student set not found.'}, status=status.HTTP_404_NOT_FOUND)
    emails = list({e.lower() for e in roster.students.values_list('email', flat=True)})
    roster.delete()
    for email in emails:
        _sync_profile_enrollment_for_email(email)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def instructor_subjects(request):
    if not _is_instructor(request.user):
        return Response({'error': 'Instructor access required.'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        archived_ids = set(request.user.archived_subjects.values_list('id', flat=True))
        qs = (
            Subject.objects.filter(Q(instructor=request.user) | Q(additional_instructors=request.user)).distinct()
            .annotate(student_count=Count('student_sets__students__email', distinct=True))
            .order_by('name')
        )
        rows = [
            {
                'id': s.id,
                'name': s.name,
                'code': s.code,
                'category': s.category,
                'created_at': s.created_at,
                'student_count': s.student_count,
                'announcements': s.announcements,
                'display_photo': s.display_photo.url if s.display_photo else None,
                'is_archived': s.id in archived_ids,
            }
            for s in qs
        ]
        return Response({'subjects': rows}, status=status.HTTP_200_OK)

    return Response({'error': 'Courses are created and assigned by an administrator.'}, status=status.HTTP_403_FORBIDDEN)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def instructor_upcoming_exams(request):
    if not _is_instructor(request.user):
        return Response({'error': 'Instructor access required.'}, status=status.HTTP_403_FORBIDDEN)

    exams = (
        ExamSet.objects.filter(
            Q(subject__instructor=request.user) | Q(subject__additional_instructors=request.user)
        )
        .select_related('subject')
        .distinct()
        .order_by('-created_at', '-id')
    )
    rows = [
        {
            'id': exam.id,
            'subject_id': exam.subject_id,
            'subject_code': exam.subject.code,
            'subject_name': exam.subject.name,
            'title': exam.title,
            'available_from': exam.available_from,
            'due_at': exam.due_at,
            'time_limit': exam.time_limit,
            'is_final': exam.is_final,
            'created_at': exam.created_at,
        }
        for exam in exams
    ]
    return Response({'exam_sets': rows}, status=status.HTTP_200_OK)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def instructor_subject_detail(request, subject_id):
    if not _is_instructor(request.user):
        return Response({'error': 'Instructor access required.'}, status=status.HTTP_403_FORBIDDEN)

    subject = Subject.objects.filter(Q(instructor=request.user) | Q(additional_instructors=request.user), id=subject_id).distinct().first()
    if not subject:
        return Response({'error': 'Subject not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'PUT':
        announcements = request.data.get('announcements')
        if not isinstance(announcements, str):
            return Response({'error': 'Announcements are required.'}, status=status.HTTP_400_BAD_REQUEST)
        subject.announcements = announcements
        subject.save(update_fields=['announcements'])
        return Response({'message': 'Announcements updated'}, status=status.HTTP_200_OK)

    if request.method == 'PATCH':
        if 'archived' in request.data:
            archived = request.data['archived']
            if not isinstance(archived, bool) or request.FILES:
                return Response({'error': 'Archive status must be true or false.'}, status=status.HTTP_400_BAD_REQUEST)
            if archived:
                subject.archived_by.add(request.user)
            else:
                subject.archived_by.remove(request.user)
            return Response({'is_archived': archived}, status=status.HTTP_200_OK)
        photo = request.FILES.get('display_photo')
        if not photo:
            return Response({'error': 'Choose a banner image.'}, status=status.HTTP_400_BAD_REQUEST)
        if photo.size > 5 * 1024 * 1024:
            return Response({'error': 'Banner images must be 5 MB or smaller.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            with Image.open(photo) as image:
                if image.format not in {'JPEG', 'PNG', 'WEBP'}:
                    raise ValueError('Unsupported image format')
                image.verify()
        except (UnidentifiedImageError, OSError, ValueError):
            return Response({'error': 'Use a valid JPG, PNG, or WebP image.'}, status=status.HTTP_400_BAD_REQUEST)
        photo.seek(0)
        subject.display_photo = photo
        subject.save(update_fields=['display_photo'])
        return Response({'display_photo': subject.display_photo.url})


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def subject_students(request, subject_id):
    if not _is_instructor(request.user):
        return Response({'error': 'Instructor access required.'}, status=status.HTTP_403_FORBIDDEN)

    subject = Subject.objects.filter(Q(instructor=request.user) | Q(additional_instructors=request.user), id=subject_id).distinct().first()
    if not subject:
        return Response({'error': 'Subject not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        qs = (
            EnrolledStudent.objects.filter(student_set__subject=subject)
            .select_related('student_set')
            .order_by('email')
        )
        student_set_id = request.query_params.get('student_set_id')
        if student_set_id:
            qs = qs.filter(student_set_id=student_set_id)
        rows = [
            {
                'id': r.id,
                'email': r.email,
                'created_at': r.created_at,
                'student_set_id': r.student_set_id,
                'student_set_name': r.student_set.name if r.student_set else None,
            }
            for r in qs
        ]
        return Response({'students': list(rows)}, status=status.HTTP_200_OK)

    email = (request.data.get('email') or '').strip().lower()
    student_set_id = request.data.get('student_set_id')
    if not email:
        return Response({'error': 'Email required.'}, status=status.HTTP_400_BAD_REQUEST)
    if not student_set_id:
        return Response({'error': 'student_set_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
    if not email.endswith(f"@{settings.ALLOWED_SCHOOL_DOMAIN}"):
        return Response(
            {'error': f"Only @{settings.ALLOWED_SCHOOL_DOMAIN} emails are allowed."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    roster = StudentSet.objects.filter(
        id=student_set_id,
        subject=subject,
    ).first()
    if not roster:
        return Response({'error': 'Student set not found for this subject.'}, status=status.HTTP_404_NOT_FOUND)

    if not UserProfile.objects.filter(user__email__iexact=email, role='student', is_enrolled=True).exists():
        return Response(
            {'error': 'This student has not been enrolled by the admin.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        enrollment, existing = _enroll_student_in_set_once(email, roster)
    except IntegrityError:
        return Response({'error': 'Student already enrolled in this set.'}, status=status.HTTP_409_CONFLICT)
    if existing:
        message = (
            f'Student already enrolled in this course through {existing.student_set.name}.'
            if existing.student_set_id != roster.id
            else 'Student already enrolled in this set.'
        )
        return Response({'error': message}, status=status.HTTP_409_CONFLICT)

    _sync_profile_enrollment_for_email(email)
    return Response(
        {
            'id': enrollment.id,
            'email': enrollment.email,
            'created_at': enrollment.created_at,
            'student_set_id': enrollment.student_set_id,
            'student_set_name': roster.name,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def subject_student_detail(request, subject_id, enrollment_id):
    if not _is_instructor(request.user):
        return Response({'error': 'Instructor access required.'}, status=status.HTTP_403_FORBIDDEN)

    enrollment = (
        EnrolledStudent.objects.select_related('student_set', 'student_set__subject')
        .filter(
            Q(student_set__subject__instructor=request.user)
            | Q(student_set__subject__additional_instructors=request.user),
            id=enrollment_id,
            student_set__subject_id=subject_id,
        )
        .distinct()
        .first()
    )
    if not enrollment:
        return Response({'error': 'Enrollment not found.'}, status=status.HTTP_404_NOT_FOUND)

    email = enrollment.email
    enrollment.delete()
    _sync_profile_enrollment_for_email(email)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def subject_sets(request, subject_id):
    if not _is_instructor(request.user):
        return Response({'error': 'Instructor access required.'}, status=status.HTTP_403_FORBIDDEN)
    subject = Subject.objects.filter(Q(instructor=request.user) | Q(additional_instructors=request.user), id=subject_id).distinct().first()
    if not subject:
        return Response({'error': 'Subject not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        rows = (
            StudentSet.objects.filter(subject=subject)
            .annotate(student_count=Count('students', distinct=True))
            .values('id', 'name', 'created_at', 'student_count')
            .order_by('name')
        )
        return Response({'sets': list(rows)}, status=status.HTTP_200_OK)

    name = (request.data.get('name') or '').strip()
    if not name:
        return Response({'error': 'Set name is required.'}, status=status.HTTP_400_BAD_REQUEST)
    if StudentSet.objects.filter(subject=subject, name__iexact=name).exists():
        return Response({'error': 'Set name already exists in this subject.'}, status=status.HTTP_409_CONFLICT)
    roster = StudentSet.objects.create(name=name, created_by=request.user, subject=subject)
    return Response(
        {'id': roster.id, 'name': roster.name, 'created_at': roster.created_at, 'student_count': 0},
        status=status.HTTP_201_CREATED,
    )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def subject_set_detail(request, subject_id, set_id):
    if not _is_instructor(request.user):
        return Response({'error': 'Instructor access required.'}, status=status.HTTP_403_FORBIDDEN)
    roster = (
        StudentSet.objects.filter(
            Q(subject__instructor=request.user) | Q(subject__additional_instructors=request.user),
            id=set_id,
            subject_id=subject_id,
        )
        .distinct()
        .prefetch_related('students')
        .first()
    )
    if not roster:
        return Response({'error': 'Student set not found.'}, status=status.HTTP_404_NOT_FOUND)
    emails = list({e.lower() for e in roster.students.values_list('email', flat=True)})
    roster.delete()
    for email in emails:
        _sync_profile_enrollment_for_email(email)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def subject_exam_sets(request, subject_id):
    if not _is_instructor(request.user):
        return Response({'error': 'Instructor access required.'}, status=status.HTTP_403_FORBIDDEN)

    subject = Subject.objects.filter(Q(instructor=request.user) | Q(additional_instructors=request.user), id=subject_id).distinct().first()
    if not subject:
        return Response({'error': 'Subject not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        rows = []
        exams = (
            ExamSet.objects.filter(subject=subject)
            .annotate(
                question_count=Count('questions', distinct=True),
                non_essay_question_count=Count(
                    'questions',
                    filter=(
                        Q(questions__isnull=False)
                        & ~Q(questions__question_type=ExamQuestion.TYPE_ESSAY)
                    ),
                    distinct=True,
                ),
            )
            .order_by('-created_at', '-id')
        )
        for exam in exams:
            rows.append(
                {
                    'id': exam.id,
                    'subject_id': subject.id,
                    'subject_code': subject.code,
                    'subject_name': subject.name,
                    'title': exam.title,
                    'description': exam.description,
                    'available_from': exam.available_from,
                    'due_at': exam.due_at,
                    'time_limit': exam.time_limit,
                    'max_attempts': exam.max_attempts,
                    'allow_backtracking': exam.allow_backtracking,
                    'is_final': exam.is_final,
                    'proctoring_restrictions': _serialize_proctoring_restrictions(exam),
                    'requires_all_restrictions': _exam_requires_all_restrictions(exam),
                    'created_at': exam.created_at,
                    'exam_file': exam.exam_file.url if exam.exam_file else None,
                    'exam_file_name': exam.exam_file.name.split('/')[-1] if exam.exam_file else None,
                }
            )
        return Response({'exam_sets': rows}, status=status.HTTP_200_OK)

    title = (request.data.get('title') or '').strip()
    description = (request.data.get('description') or '').strip()
    available_from_raw = (request.data.get('available_from') or '').strip()
    due_at_raw = (request.data.get('due_at') or '').strip()
    exam_file = request.FILES.get('exam_file')
    question_file_format = request.data.get('question_file_format', 'auto')
    max_attempts_raw = request.data.get('max_attempts', 1)
    time_limit_raw = request.data.get('time_limit', 60)
    allow_backtracking_raw = request.data.get('allow_backtracking', 'true')
    if str(allow_backtracking_raw).lower() not in ('true', 'false'):
        return Response({'error': 'Invalid question navigation setting.'}, status=status.HTTP_400_BAD_REQUEST)
    assigned_sets_raw = request.data.get('assigned_sets', '[]')
    if not title:
        return Response({'error': 'Exam set title is required.'}, status=status.HTTP_400_BAD_REQUEST)
    if not due_at_raw:
        return Response({'error': 'Due date is required.'}, status=status.HTTP_400_BAD_REQUEST)

    parsed_questions = []
    if exam_file:
        try:
            parsed_questions = _parse_uploaded_exam(exam_file, question_file_format)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    
    available_from_value = None
    if available_from_raw:
        available_from_value = parse_datetime(available_from_raw)
        if available_from_value is None:
            available_date_value = parse_date(available_from_raw)
            if available_date_value is None:
                 return Response({'error': 'Invalid start date format.'}, status=status.HTTP_400_BAD_REQUEST)
            available_from_value = datetime.combine(available_date_value, time(hour=0, minute=0, second=0))
        if timezone.is_naive(available_from_value):
            available_from_value = timezone.make_aware(available_from_value, timezone.get_current_timezone())

    due_at_value = parse_datetime(due_at_raw)
    if due_at_value is None:
        due_date_value = parse_date(due_at_raw)
        if due_date_value is None:
            return Response({'error': 'Invalid due date format.'}, status=status.HTTP_400_BAD_REQUEST)
        # Date-only inputs are treated as end-of-day local time.
        due_at_value = datetime.combine(due_date_value, time(hour=23, minute=59, second=59))
    if timezone.is_naive(due_at_value):
        due_at_value = timezone.make_aware(due_at_value, timezone.get_current_timezone())
    exam_set = ExamSet.objects.create(
        subject=subject,
        title=title,
        description=description,
        available_from=available_from_value,
        due_at=due_at_value,
        # The uploaded text is a bank import, not an attachment to this exam.
        exam_file=None,
        max_attempts=int(max_attempts_raw) if str(max_attempts_raw).isdigit() else 1,
        time_limit=int(time_limit_raw) if str(time_limit_raw).isdigit() else 60,
        allow_backtracking=str(allow_backtracking_raw).lower() == 'true',
    )

    try:
        import json
        assigned_set_ids = json.loads(assigned_sets_raw)
        if isinstance(assigned_set_ids, list) and len(assigned_set_ids) > 0:
            exam_set.assigned_sets.set(assigned_set_ids)
    except:
        pass

    if parsed_questions:
        batch = QuestionBankBatch.objects.create(subject=subject, name=f'{title} upload'[:160])
        QuestionBankItem.objects.bulk_create([
            QuestionBankItem(subject=subject, batch=batch, **question)
            for question in parsed_questions
        ])
    return Response(
        {
            'id': exam_set.id,
            'subject_id': subject.id,
            'subject_code': subject.code,
            'subject_name': subject.name,
            'title': exam_set.title,
            'description': exam_set.description,
            'available_from': exam_set.available_from,
            'due_at': exam_set.due_at,
            'allow_backtracking': exam_set.allow_backtracking,
            'proctoring_restrictions': _serialize_proctoring_restrictions(exam_set),
            'requires_all_restrictions': _exam_requires_all_restrictions(exam_set),
            'created_at': exam_set.created_at,
            'exam_file': exam_set.exam_file.url if exam_set.exam_file else None,
            'exam_file_name': exam_set.exam_file.name.split('/')[-1] if exam_set.exam_file else None,
            'bank_questions_added': len(parsed_questions),
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(['DELETE', 'PATCH'])
@permission_classes([IsAuthenticated])
def subject_exam_set_detail(request, subject_id, exam_set_id):
    if not _is_instructor(request.user):
        return Response({'error': 'Instructor access required.'}, status=status.HTTP_403_FORBIDDEN)

    exam_set = ExamSet.objects.filter(
        Q(subject__instructor=request.user) | Q(subject__additional_instructors=request.user),
        id=exam_set_id,
        subject_id=subject_id,
    ).distinct().first()
    if not exam_set:
        return Response({'error': 'Exam set not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'PATCH':
        if exam_set.is_final:
            return Response(
                {'error': 'A finalized exam cannot be changed.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        restrictions = request.data.get('proctoring_restrictions')
        if not isinstance(restrictions, dict):
            return Response(
                {'error': 'proctoring_restrictions must be an object.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            requested = {
                key: _request_boolean(restrictions.get(key, getattr(exam_set, field)))
                for key, field in PROCTORING_RESTRICTION_FIELDS.items()
            }
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        requires_all = _exam_requires_all_restrictions(exam_set)
        if requires_all and not all(requested.values()):
            _enable_all_proctoring_restrictions(exam_set)
            return Response(
                {'error': 'Add at least one essay question before customizing proctoring restrictions.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        for key, field in PROCTORING_RESTRICTION_FIELDS.items():
            setattr(exam_set, field, requested[key])
        exam_set.save(update_fields=list(PROCTORING_RESTRICTION_FIELDS.values()))
        return Response({
            'proctoring_restrictions': _serialize_proctoring_restrictions(exam_set),
            'requires_all_restrictions': requires_all,
        })

    # Wipe student submissions, answers, proctoring logs/evidence, and integrity
    # reports first so Exam Progress and student history do not keep orphans.
    from django.db import transaction
    with transaction.atomic():
        _purge_exam_set_student_records(exam_set)
        if exam_set.exam_file:
            exam_set.exam_file.delete(save=False)
        exam_set.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def exam_set_stats(request, subject_id, exam_set_id):
    """Returns the count of students who took the exam per set in the subject."""
    if not _is_instructor(request.user):
        return Response({'error': 'Instructor access required.'}, status=status.HTTP_403_FORBIDDEN)

    exam_set = (
        ExamSet.objects.filter(
            Q(subject__instructor=request.user) | Q(subject__additional_instructors=request.user),
            id=exam_set_id,
            subject_id=subject_id,
        )
        .distinct()
        .prefetch_related('assigned_sets')
        .first()
    )
    if not exam_set:
        return Response({'error': 'Exam set not found.'}, status=status.HTTP_404_NOT_FOUND)

    students = EnrolledStudent.objects.filter(
        student_set__subject_id=subject_id,
    ).select_related('student_set')
    
    submissions = list(
        ExamSubmission.objects.filter(exam_set=exam_set).select_related('exam_set')
    )
    submission_map = {sub.student_email.lower(): sub for sub in submissions}
    gaze_counts = _bulk_gaze_strike_counts(submissions)

    assigned_ids = {assigned_set.id for assigned_set in exam_set.assigned_sets.all()}

    now = timezone.now()
    is_overdue = bool(exam_set.due_at and now > exam_set.due_at)

    set_stats = {}
    examinees = []

    for st in students:
        s_id = st.student_set.id
        s_name = st.student_set.name
        
        if assigned_ids and s_id not in assigned_ids:
            continue

        if s_id not in set_stats:
            set_stats[s_id] = {'id': s_id, 'name': s_name, 'total': 0, 'done': 0}
        
        set_stats[s_id]['total'] += 1
        
        sub = submission_map.get(st.email.lower())
        
        status_text = 'Not Taken' if is_overdue else 'Not Started'
        tab_switches = 0
        gaze_v = 0
        gaze_nf = 0
        terminated = False
        snapshot_url = None
        
        if sub:
            if sub.is_done:
                set_stats[s_id]['done'] += 1
                status_text = 'Terminated' if sub.terminated else 'Done'
            else:
                status_text = 'Not Taken' if is_overdue else 'In Progress'
            
            terminated = sub.terminated
            tab_switches = sub.tab_switches
            strikes = gaze_counts[sub.id]
            gaze_v = strikes['gaze_violation_count']
            gaze_nf = strikes['gaze_no_face_count']
            snapshot_url = _submission_snapshot_url(sub, request)

        examinees.append({
            'name': st.email,
            'email': st.email,
            'set_name': s_name,
            'status': status_text,
            'tab_switches': tab_switches,
            'gaze_violation_count': gaze_v,
            'gaze_no_face_count': gaze_nf,
            'terminated': terminated,
            'snapshot_url': snapshot_url,
        })

    stats_list = list(set_stats.values())
    stats_list.sort(key=lambda x: x['name'])
    
    return Response({
        'exam_id': exam_set.id,
        'title': exam_set.title,
        'sets': stats_list,
        'examinees': examinees
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def instructor_submission_snapshot(request, subject_id, exam_set_id, submission_id):
    """Stream a live snapshot through the authenticated API.

    This keeps object-storage credentials and signed storage URLs out of the
    browser and works with both local media and remote storage backends.
    """
    if not _is_instructor(request.user):
        return Response({'error': 'Instructor access required.'}, status=status.HTTP_403_FORBIDDEN)

    submission = ExamSubmission.objects.filter(
        Q(exam_set__subject__instructor=request.user) | Q(exam_set__subject__additional_instructors=request.user),
        pk=submission_id,
        exam_set_id=exam_set_id,
        exam_set__subject_id=subject_id,
    ).distinct().only('latest_snapshot').first()
    if not submission or not submission.latest_snapshot:
        return Response({'error': 'Snapshot not found.'}, status=status.HTTP_404_NOT_FOUND)

    try:
        snapshot_file = submission.latest_snapshot.open('rb')
    except Exception:
        return Response({'error': 'Snapshot not found.'}, status=status.HTTP_404_NOT_FOUND)

    response = FileResponse(snapshot_file, content_type='image/jpeg')
    response['Cache-Control'] = 'private, no-store'
    return response


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def subject_exam_progress(request, subject_id):
    if not _is_instructor(request.user):
        return Response({'error': 'Instructor access required.'}, status=status.HTTP_403_FORBIDDEN)

    subject = Subject.objects.filter(Q(instructor=request.user) | Q(additional_instructors=request.user), id=subject_id).distinct().first()
    if not subject:
        return Response({'error': 'Subject not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'POST':
        exam_set_id = request.data.get('exam_set_id')
        student_email = (request.data.get('student_email') or '').strip().lower()
        is_done_raw = request.data.get('is_done')
        is_done = str(is_done_raw).lower() in ('1', 'true', 'yes', 'on')
        score = request.data.get('score')
        integrity_score = request.data.get('integrity_score')
        submitted_at_raw = (request.data.get('submitted_at') or '').strip()

        if not exam_set_id or not student_email:
            return Response({'error': 'exam_set_id and student_email are required.'}, status=status.HTTP_400_BAD_REQUEST)
        exam_set = ExamSet.objects.filter(id=exam_set_id, subject=subject).first()
        if not exam_set:
            return Response({'error': 'Exam set not found for this subject.'}, status=status.HTTP_404_NOT_FOUND)

        submitted_at_value = parse_datetime(submitted_at_raw) if submitted_at_raw else timezone.now()
        if submitted_at_raw and submitted_at_value is None:
            return Response({'error': 'Invalid submitted_at format.'}, status=status.HTTP_400_BAD_REQUEST)
        if submitted_at_value and timezone.is_naive(submitted_at_value):
            submitted_at_value = timezone.make_aware(submitted_at_value, timezone.get_current_timezone())

        submission, _ = ExamSubmission.objects.update_or_create(
            exam_set=exam_set,
            student_email=student_email,
            defaults={
                'is_done': is_done,
                'score': score if is_done else None,
                'integrity_score': integrity_score if is_done else None,
                'submitted_at': submitted_at_value if is_done else None,
            },
        )
        return Response(
            {
                'id': submission.id,
                'exam_set_id': submission.exam_set_id,
                'student_email': submission.student_email,
                'is_done': submission.is_done,
                'score': submission.score,
                'integrity_score': submission.integrity_score,
                'submitted_at': submission.submitted_at,
            },
            status=status.HTTP_200_OK,
        )

    # Build a map: email -> (set_id, set_name)
    enrollment_qs = (
        EnrolledStudent.objects.filter(
            student_set__subject=subject,
        )
        .select_related('student_set')
    )
    email_to_set = {}
    for enr in enrollment_qs:
        email_to_set[enr.email.lower()] = {
            'set_id': enr.student_set.id,
            'set_name': enr.student_set.name,
        }

    student_emails = list(email_to_set.keys())
    exams = list(
        ExamSet.objects.filter(subject=subject)
        .prefetch_related('assigned_sets', 'questions')
        .order_by('-created_at', '-id')
    )
    submissions = list(ExamSubmission.objects.filter(exam_set__subject=subject))
    submission_map = {
        (row.exam_set_id, row.student_email.lower()): row
        for row in submissions
    }
    gaze_counts = _bulk_gaze_strike_counts(submissions)
    integrity_report_keys = set(
        ExamIntegrityReport.objects.filter(submission__exam_set__subject=subject)
        .values_list('submission_id', 'attempt_number')
    )
    graded_subjective_counts = {}
    graded_answers = StudentAnswer.objects.filter(
        exam_set__subject=subject,
        question__question_type=ExamQuestion.TYPE_ESSAY,
        awarded_points__isnull=False,
    ).values_list('exam_set_id', 'student_email')
    for exam_id, email in graded_answers:
        key = (exam_id, email.lower())
        graded_subjective_counts[key] = graded_subjective_counts.get(key, 0) + 1

    rows = []
    for exam in exams:
        assigned_ids = {assigned_set.id for assigned_set in exam.assigned_sets.all()}
        subjective_question_ids = {
            question.id
            for question in exam.questions.all()
            if question.question_type == ExamQuestion.TYPE_ESSAY
        }
        
        for email in student_emails:
            set_info = email_to_set.get(email.lower(), {})
            s_id = set_info.get('set_id')
            
            # Skip this student if the exam is restricted to specific sets and their set isn't one of them
            if assigned_ids and s_id not in assigned_ids:
                continue

            sub = submission_map.get((exam.id, email.lower()))
            gaze_v = 0
            gaze_nf = 0
            gadget_count = 0
            if sub:
                strikes = gaze_counts[sub.id]
                gaze_v = strikes['gaze_violation_count']
                gaze_nf = strikes['gaze_no_face_count']
                gadget_count = strikes['gadget_detection_count']
            graded_subjective_count = graded_subjective_counts.get((exam.id, email), 0)
            pending_subjective_count = max(
                0,
                len(subjective_question_ids) - graded_subjective_count,
            ) if sub and sub.is_done else 0
            rows.append(
                {
                    'exam_set_id': exam.id,
                    'exam_title': exam.title,
                    'created_at': exam.created_at,
                    'available_from': exam.available_from,
                    'due_at': exam.due_at,
                    'student_email': email,
                    'student_set_id': s_id,
                    'student_set_name': set_info.get('set_name'),
                    'is_done': bool(sub and sub.is_done),
                    'score': sub.score if sub and sub.is_done else None,
                    'integrity_score': sub.integrity_score if sub and sub.is_done else None,
                    'submitted_at': sub.submitted_at if sub and sub.is_done else None,
                    'started_at': sub.started_at if sub else None,
                    'terminated': bool(sub and sub.terminated),
                    'tab_switches': sub.tab_switches if sub else 0,
                    'gaze_violation_count': gaze_v,
                    'gaze_no_face_count': gaze_nf,
                    'gadget_detection_count': gadget_count,
                    'subjective_count': len(subjective_question_ids),
                    'pending_subjective_count': pending_subjective_count,
                    'manual_grading_complete': bool(subjective_question_ids) and pending_subjective_count == 0,
                    'has_integrity_report': bool(
                        sub and sub.is_done and (
                            sub.integrity_score is not None
                            or (sub.id, sub.attempt_count) in integrity_report_keys
                        )
                    ),
                }
            )
    return Response({'progress': rows}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_student_sets(request):
    """
    Returns the roster set(s) the currently logged-in student belongs to.
    """
    rows = (
        EnrolledStudent.objects.filter(email__iexact=request.user.email)
        .select_related('student_set')
        .values('student_set__id', 'student_set__name')
    )
    # unique by student_set id
    sets = []
    seen = set()
    for r in rows:
        sid = r['student_set__id']
        if sid in seen:
            continue
        seen.add(sid)
        sets.append({'id': sid, 'name': r['student_set__name']})

    return Response({'sets': sets}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_subjects(request):
    rows = (
        EnrolledStudent.objects.filter(
            email__iexact=request.user.email,
            student_set__subject__isnull=False,
        )
        .select_related('student_set', 'student_set__subject', 'student_set__subject__instructor')
        .order_by('student_set__subject__name')
    )
    subjects = []
    seen = set()
    for row in rows:
        subject = row.student_set.subject
        if subject.id in seen:
            continue
        seen.add(subject.id)
        instructor_name = (
            subject.instructor.get_full_name().strip()
            or subject.instructor.username
        )
        subjects.append(
            {
                'id': subject.id,
                'name': subject.name,
                'code': subject.code,
                'instructor_name': instructor_name,
                'announcements': subject.announcements,
                'display_photo': subject.display_photo.url if subject.display_photo else None,
            }
        )
    return Response({'subjects': subjects}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_exam_sets(request):
    student_email = request.user.email
    subject_exams = (
        ExamSet.objects.filter(
            subject__student_sets__students__email__iexact=student_email,
            is_final=True,
        )
        .filter(
            Q(assigned_sets__isnull=True)
            | Q(assigned_sets__students__email__iexact=student_email)
        )
        .select_related('subject')
        .distinct()
        .order_by('-created_at', '-id')
    )

    submissions = ExamSubmission.objects.filter(
        student_email__iexact=student_email,
    ).values('exam_set_id', 'score', 'is_done', 'terminated', 'attempt_count')
    submission_dict = {s['exam_set_id']: s for s in submissions}

    exams = []
    for exam in subject_exams:
        submission = submission_dict.get(exam.id, {})
        exams.append(
            {
                'id': exam.id,
                'title': exam.title,
                'description': exam.description,
                'available_from': exam.available_from,
                'due_at': exam.due_at,
                'time_limit': exam.time_limit,
                'max_attempts': exam.max_attempts,
                'attempt_count': submission.get('attempt_count', 0),
                'is_final': exam.is_final,
                'created_at': exam.created_at,
                'subject_id': exam.subject_id,
                'subject_name': exam.subject.name,
                'subject_code': exam.subject.code,
                'exam_file': exam.exam_file.url if exam.exam_file else None,
                'exam_file_name': exam.exam_file.name.split('/')[-1] if exam.exam_file else None,
                'is_done': bool(submission.get('is_done')),
                'terminated': bool(submission.get('terminated')),
                'score': submission.get('score') if submission.get('is_done') else None,
            }
        )
    return Response({'exam_sets': exams}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def google_login(request):
    id_token = request.data.get('token')
    if not id_token:
        return Response({'error': 'Token required'}, status=status.HTTP_400_BAD_REQUEST)

    import time
    try:
        try:
            decoded = firebase_auth.verify_id_token(id_token)
        except firebase_auth.InvalidIdTokenError as e:
            if "used too early" in str(e).lower():
                print("Token used too early! Sleeping 2 seconds for clock skew...")
                time.sleep(2)
                decoded = firebase_auth.verify_id_token(id_token)
            else:
                raise

        email = decoded.get('email', '')

        if not email.endswith(f"@{settings.ALLOWED_SCHOOL_DOMAIN}"):
            return Response(
                {'error': 'Only school accounts allowed.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        full_name = decoded.get('name', '')
        name_parts = full_name.split()

        user, _ = User.objects.get_or_create(
            username=email,
            defaults={
                'email': email,
                'first_name': name_parts[0] if name_parts else '',
                'last_name': ' '.join(name_parts[1:]) if len(name_parts) > 1 else '',
            },
        )

        if not user.is_active:
            return Response(
                {'error': 'This account is inactive. Contact an administrator.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        picture = decoded.get('picture') or ''
        profile, _ = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                'role': 'student',
                'google_photo': picture,
                'is_enrolled': False,
            },
        )
        profile.google_photo = picture or profile.google_photo
        profile.save(update_fields=['google_photo'])

        # Allow instructors (is_staff=True) to login via Google — skip enrollment check
        if profile.role == 'instructor' or user.is_staff:
            profile.role = 'instructor'
            profile.save(update_fields=['role'])
            refresh = RefreshToken.for_user(user)
            return Response(
                {
                    'access_token': str(refresh.access_token),
                    'refresh_token': str(refresh),
                    'user': {
                        'email': user.email,
                        'name': full_name,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'mobile_number': profile.mobile_number,
                        'photo': _get_profile_photo_url(request, profile),
                        'role': 'instructor',
                        'face_photo_url': request.build_absolute_uri(profile.face_photo.url) if profile.face_photo else None,
                        'face_registered': bool(profile.face_encoding),
                    },
                },
                status=status.HTTP_200_OK,
            )

        if profile.role == 'student' and not profile.is_enrolled:
            return Response(
                {'error': 'You are not enrolled. Please contact the admin.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                'access_token': str(refresh.access_token),
                'refresh_token': str(refresh),
                'user': {
                    'email': user.email,
                    'name': full_name,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'mobile_number': profile.mobile_number,
                    'photo': _get_profile_photo_url(request, profile),
                    'role': profile.role,
                    'face_photo_url': request.build_absolute_uri(profile.face_photo.url) if profile.face_photo and profile.id_verified_at else None,
                    'face_pending_photo_url': None,
                    'face_registered': bool(profile.face_encoding and profile.id_verified_at),
                    'face_status': _effective_face_status(profile),
                    'face_reupload_allowed': profile.face_reupload_allowed,
                },
            },
            status=status.HTTP_200_OK,
        )


    except firebase_auth.InvalidIdTokenError as e:
        print("Firebase InvalidIdTokenError:", e)
        return Response({'error': f'Invalid token: {e}'}, status=status.HTTP_401_UNAUTHORIZED)
    except Exception as exc:
        return Response({'error': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _get_profile_photo_url(request, profile):
    """Return custom uploaded photo if exists, else google photo."""
    if profile.custom_photo and hasattr(profile.custom_photo, 'url'):
        return request.build_absolute_uri(profile.custom_photo.url)
    return profile.google_photo


PROCTORING_RESTRICTION_FIELDS = {
    'gaze_above': 'detect_gaze_above',
    'gaze_below': 'detect_gaze_below',
    'gaze_left': 'detect_gaze_left',
    'gaze_right': 'detect_gaze_right',
    'gadgets': 'detect_gadgets',
}


def _serialize_proctoring_restrictions(exam_set):
    return {
        key: bool(getattr(exam_set, field))
        for key, field in PROCTORING_RESTRICTION_FIELDS.items()
    }


def _exam_requires_all_restrictions(exam_set):
    if hasattr(exam_set, 'question_count') and hasattr(exam_set, 'non_essay_question_count'):
        return (
            exam_set.question_count == 0
            or exam_set.question_count == exam_set.non_essay_question_count
        )
    questions = exam_set.questions.all()
    return (
        not questions.exists()
        or not questions.filter(question_type=ExamQuestion.TYPE_ESSAY).exists()
    )


def _enable_all_proctoring_restrictions(exam_set):
    update_fields = []
    for field in PROCTORING_RESTRICTION_FIELDS.values():
        if not getattr(exam_set, field):
            setattr(exam_set, field, True)
            update_fields.append(field)
    if update_fields:
        exam_set.save(update_fields=update_fields)


def _request_boolean(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    normalized = str(value).strip().lower()
    if normalized in ('true', '1', 'yes', 'on'):
        return True
    if normalized in ('false', '0', 'no', 'off'):
        return False
    raise ValueError('Restriction values must be booleans.')


def _parse_uploaded_exam(upload, requested_format='auto'):
    """Parse an uploaded question file before creating the exam.

    Text uploads support Aiken multiple-choice files and essay prompts separated
    by a blank line. The explicit format sent by the instructor UI removes any
    ambiguity, while ``auto`` keeps older clients working.
    """
    filename = upload.name.lower()
    if not filename.endswith(('.txt', '.iken', '.csv')):
        raise ValueError('Question files must be .txt, .iken, or .csv.')
    if upload.size > 5 * 1024 * 1024:
        raise ValueError('Question files must be 5 MB or smaller.')

    try:
        upload.seek(0)
        content = upload.read().decode('utf-8-sig')
    except UnicodeDecodeError as exc:
        raise ValueError('Question files must use UTF-8 text encoding.') from exc
    finally:
        upload.seek(0)

    requested_format = str(requested_format or 'auto').strip().lower()
    if requested_format not in {'auto', 'aiken', 'essay'}:
        raise ValueError('question_file_format must be auto, aiken, or essay.')

    questions = []
    if filename.endswith('.csv'):
        reader = csv.reader(io.StringIO(content))
        header = next(reader, None)
        for row in reader:
            if not row or not row[0].strip():
                continue
            question_text = row[0].strip()
            question_type = (row[1].strip().lower() if len(row) > 1 else '') or ExamQuestion.TYPE_MULTIPLE_CHOICE
            if question_type not in {choice[0] for choice in ExamQuestion.QUESTION_TYPE_CHOICES}:
                question_type = ExamQuestion.TYPE_MULTIPLE_CHOICE
            correct_answer = row[2].strip() if len(row) > 2 and row[2].strip() else None
            choices = [cell.strip() for cell in row[3:] if cell.strip()]
            if question_type == ExamQuestion.TYPE_ESSAY:
                correct_answer = None
                choices = None
            elif question_type != ExamQuestion.TYPE_MULTIPLE_CHOICE:
                choices = None
            questions.append({
                'question_type': question_type,
                'question_text': question_text,
                'choices': choices,
                'correct_answer': correct_answer,
            })
    else:
        is_aiken = requested_format == 'aiken' or (
            requested_format == 'auto'
            and any(line.strip().upper().startswith('ANSWER:') for line in content.splitlines())
        )
        if is_aiken:
            question_text = ''
            choices = []
            for raw_line in [*content.splitlines(), '']:
                line = raw_line.strip()
                if not line:
                    continue
                if line.upper().startswith('ANSWER:'):
                    answer_letter = line[7:].strip().upper()
                    clean_choices = []
                    correct_answer = None
                    for choice in choices:
                        parts = choice.split(maxsplit=1)
                        prefix = parts[0].rstrip('.)').upper() if parts else ''
                        choice_text = parts[1].strip() if len(parts) > 1 else ''
                        if choice_text:
                            clean_choices.append(choice_text)
                        if prefix == answer_letter:
                            correct_answer = choice_text
                    if not question_text or len(clean_choices) < 2 or not correct_answer:
                        raise ValueError('Invalid Aiken file. Each question needs at least two choices and a valid ANSWER letter.')
                    questions.append({
                        'question_type': ExamQuestion.TYPE_MULTIPLE_CHOICE,
                        'question_text': question_text,
                        'choices': clean_choices,
                        'correct_answer': correct_answer,
                    })
                    question_text = ''
                    choices = []
                elif not question_text:
                    question_text = line
                else:
                    choices.append(line)
            if question_text or choices:
                raise ValueError('Invalid Aiken file. The last question is missing an ANSWER line.')
        else:
            prompts = [part.strip() for part in re.split(r'\r?\n\s*\r?\n', content) if part.strip()]
            for prompt in prompts:
                prompt = re.sub(r'^\s*(?:essay|question)\s*:\s*', '', prompt, flags=re.IGNORECASE).strip()
                if prompt:
                    questions.append({
                        'question_type': ExamQuestion.TYPE_ESSAY,
                        'question_text': prompt,
                        'choices': None,
                        'correct_answer': None,
                    })

    if not questions:
        raise ValueError('No valid questions were found in the uploaded file.')
    return questions


def _question_uses_custom_restrictions(exam_set, question_id):
    """Customized restriction toggles apply only while answering an essay."""
    try:
        question_id = int(question_id)
    except (TypeError, ValueError):
        return False
    return ExamQuestion.objects.filter(
        pk=question_id,
        exam_set=exam_set,
        question_type=ExamQuestion.TYPE_ESSAY,
    ).exists()


def _gaze_direction_enabled(exam_set, label, question_id=None):
    if not _question_uses_custom_restrictions(exam_set, question_id):
        return True
    normalized = str(label or '').lower()
    if 'above' in normalized:
        return exam_set.detect_gaze_above
    if 'below' in normalized:
        return exam_set.detect_gaze_below
    if 'left' in normalized and 'right' not in normalized:
        return exam_set.detect_gaze_left
    if 'right' in normalized and 'left' not in normalized:
        return exam_set.detect_gaze_right
    return True

# ---------------------------------------------------------------------------
# PROFILE SETTINGS
# ---------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def update_profile(request):
    """Update the logged-in user's profile settings (including picture upload)."""
    user = request.user
    profile = getattr(user, 'profile', None)
    if not profile:
        return Response({'error': 'Profile not found.'}, status=status.HTTP_404_NOT_FOUND)

    first_name = request.data.get('first_name', user.first_name)
    last_name = request.data.get('last_name', user.last_name)
    if profile.role == 'student' and (
        first_name != user.first_name or last_name != user.last_name
    ):
        return Response({'error': 'Student account names are managed by the administrator. Contact the admin to correct your name.'}, status=status.HTTP_400_BAD_REQUEST)
    mobile_number = request.data.get('mobile_number', profile.mobile_number)

    user.first_name = first_name
    user.last_name = last_name
    user.save(update_fields=['first_name', 'last_name'])

    profile.mobile_number = mobile_number

    if 'custom_photo' in request.FILES:
        profile.custom_photo = request.FILES['custom_photo']

    if 'face_photo' in request.FILES:
        if profile.role != 'student':
            return Response({'error': 'Student ID verification is only available to students.'}, status=status.HTTP_403_FORBIDDEN)
        is_locked = (
            bool(profile.id_verified_at)
            and profile.face_status == UserProfile.FACE_STATUS_APPROVED
            and not profile.face_reupload_allowed
        )
        if is_locked:
            return Response({'error': 'Your student ID is already verified. Contact the admin to allow a new submission.'}, status=status.HTTP_400_BAD_REQUEST)
        from .student_id_service import StudentIdError, verify_student_id
        import json as _json
        import uuid
        uploaded = request.FILES['face_photo']
        file_extension = {'image/jpeg': 'jpg', 'image/png': 'png', 'image/webp': 'webp'}.get(uploaded.content_type)
        if not file_extension:
            return Response({'error': 'Upload a JPG, PNG, or WebP student ID photo.'}, status=status.HTTP_400_BAD_REQUEST)
        if uploaded.size > 5 * 1024 * 1024:
            return Response({'error': 'Upload a student ID image under 5 MB.'}, status=status.HTTP_400_BAD_REQUEST)
        image_bytes = uploaded.read()
        try:
            encoding = verify_student_id(image_bytes, user.first_name, user.last_name)
        except StudentIdError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            import logging
            logging.getLogger(__name__).exception('Student ID verification failed')
            return Response({'error': 'Student ID verification is unavailable. Please try again later.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        profile.face_photo.save(f'{uuid.uuid4().hex}.{file_extension}', ContentFile(image_bytes), save=False)
        profile.face_encoding = _json.dumps(encoding)
        profile.id_verified_at = timezone.now()
        profile.face_status = UserProfile.FACE_STATUS_APPROVED
        profile.face_reupload_allowed = False
        profile.face_pending_photo = None

    profile.save()

    full_name = f"{user.first_name} {user.last_name}".strip() or user.email

    response_data = {
        'user': {
            'email': user.email,
            'name': full_name,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'mobile_number': profile.mobile_number,
            'photo': _get_profile_photo_url(request, profile),
            'role': profile.role,
            'face_photo_url': request.build_absolute_uri(profile.face_photo.url) if profile.face_photo and profile.id_verified_at else None,
            'face_pending_photo_url': request.build_absolute_uri(profile.face_pending_photo.url) if profile.face_pending_photo else None,
            'face_registered': bool(profile.face_encoding and profile.id_verified_at),
            'face_status': _effective_face_status(profile),
            'face_reupload_allowed': profile.face_reupload_allowed,
        }
    }
    return Response(response_data)

# ---------------------------------------------------------------------------
# INSTRUCTOR – Exam Question CRUD
# ---------------------------------------------------------------------------

def _serialize_question(q, include_answer=True):
    """Return a dict representation of an ExamQuestion."""
    data = {
        'id': q.id,
        'order': q.order,
        'question_type': q.question_type,
        'question_text': q.question_text,
        'choices': q.choices or [],
        'points': q.points,
        'max_words': q.max_words,
        'case_sensitive': q.case_sensitive,
        'created_at': q.created_at,
        'bank_item_id': q.bank_item_id,
    }
    if include_answer:
        data['correct_answer'] = q.correct_answer
    return data


def _serialize_bank_item(item):
    return {
        'id': item.id,
        'batch_id': item.batch_id,
        'question_type': item.question_type,
        'question_text': item.question_text,
        'choices': item.choices or [],
        'correct_answer': item.correct_answer,
        'points': item.points,
        'max_words': item.max_words,
        'case_sensitive': item.case_sensitive,
        'created_at': item.created_at,
    }


def _serialize_bank_batch(batch):
    return {
        'id': batch.id,
        'name': batch.name,
        'created_at': batch.created_at,
    }


def _bank_batch_for_manual_question(subject, data):
    batch_id = data.get('batch_id')
    if batch_id not in (None, ''):
        try:
            batch_id = int(batch_id)
        except (TypeError, ValueError):
            raise ValueError('Question batch not found in this course.') from None
        batch = QuestionBankBatch.objects.filter(subject=subject, id=batch_id).first()
        if not batch:
            raise ValueError('Question batch not found in this course.')
        return batch
    name = str(data.get('batch_name') or 'Manual questions').strip()[:160]
    if not name:
        raise ValueError('Batch name is required.')
    if data.get('create_new_batch') in (True, 'true', 'True', '1', 1):
        return QuestionBankBatch.objects.create(subject=subject, name=name)
    batch = QuestionBankBatch.objects.filter(subject=subject, name=name).order_by('id').first()
    return batch or QuestionBankBatch.objects.create(subject=subject, name=name)


def _question_fields_from_payload(data):
    question_text = (data.get('question_text') or '').strip()
    question_type = (data.get('question_type') or '').strip()
    choices_raw = data.get('choices')
    correct_answer = (data.get('correct_answer') or '').strip() or None
    points_raw = data.get('points')
    max_words_raw = data.get('max_words')
    case_sensitive = data.get('case_sensitive', False) in (True, 'true', 'True', '1', 1)
    valid_types = {choice[0] for choice in ExamQuestion.QUESTION_TYPE_CHOICES}
    if not question_text:
        raise ValueError('question_text is required.')
    if question_type not in valid_types:
        raise ValueError(f"question_type must be one of: {', '.join(sorted(valid_types))}.")
    choices = None
    points = None
    max_words = None
    if question_type == ExamQuestion.TYPE_MULTIPLE_CHOICE:
        if not isinstance(choices_raw, list) or len(choices_raw) < 2:
            raise ValueError('Multiple choice questions require at least 2 choices.')
        choices = [str(choice).strip() for choice in choices_raw if str(choice).strip()]
        if len(choices) < 2:
            raise ValueError('Multiple choice questions require at least 2 choices.')
        if not correct_answer:
            raise ValueError('correct_answer is required for multiple choice questions.')
        if correct_answer not in choices:
            raise ValueError('correct_answer must be one of the provided choices.')
        case_sensitive = False
    elif question_type in {ExamQuestion.TYPE_ENUMERATION, ExamQuestion.TYPE_ESSAY}:
        try:
            points = int(points_raw) if points_raw not in (None, '') else None
        except (ValueError, TypeError):
            raise ValueError('points must be a positive number.') from None
        if points is not None and points < 1:
            raise ValueError('points must be a positive number.')
    if question_type == ExamQuestion.TYPE_ESSAY:
        try:
            max_words = int(max_words_raw) if max_words_raw not in (None, '') else None
        except (ValueError, TypeError):
            raise ValueError('max_words must be a positive number.') from None
        if max_words is not None and not 1 <= max_words <= 10000:
            raise ValueError('max_words must be between 1 and 10000.')
        correct_answer = None
        case_sensitive = False
    return {
        'question_type': question_type,
        'question_text': question_text,
        'choices': choices,
        'correct_answer': correct_answer,
        'points': points,
        'max_words': max_words,
        'case_sensitive': case_sensitive,
    }


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def subject_question_bank(request, subject_id):
    """Course-scoped reusable question library for assigned instructors."""
    if not _is_instructor(request.user):
        return Response({'error': 'Instructor access required.'}, status=status.HTTP_403_FORBIDDEN)
    subject = Subject.objects.filter(
        Q(instructor=request.user) | Q(additional_instructors=request.user), id=subject_id,
    ).distinct().first()
    if not subject:
        return Response({'error': 'Subject not found.'}, status=status.HTTP_404_NOT_FOUND)
    if request.method == 'GET':
        batches = QuestionBankBatch.objects.filter(subject=subject).prefetch_related('questions')
        return Response({
            'batches': [
                {**_serialize_bank_batch(batch), 'questions': [_serialize_bank_item(item) for item in batch.questions.all()]}
                for batch in batches
            ],
        })

    upload = request.FILES.get('question_file')
    bulk_text = request.data.get('bulk_text')
    if upload or bulk_text is not None:
        if upload and bulk_text is not None:
            return Response({'error': 'Choose a file or pasted text, not both.'}, status=status.HTTP_400_BAD_REQUEST)
        if not upload:
            upload = ContentFile(str(bulk_text).encode('utf-8'), name='questions.txt')
        try:
            parsed = _parse_uploaded_exam(upload, request.data.get('question_file_format', 'auto'))
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        if any(fields['question_type'] == ExamQuestion.TYPE_ESSAY for fields in parsed):
            try:
                essay_settings = _question_fields_from_payload({
                    'question_type': ExamQuestion.TYPE_ESSAY,
                    'question_text': 'Imported essay',
                    'points': request.data.get('points'),
                    'max_words': request.data.get('max_words'),
                })
            except ValueError as exc:
                return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
            for fields in parsed:
                if fields['question_type'] == ExamQuestion.TYPE_ESSAY:
                    fields['points'] = essay_settings['points']
                    fields['max_words'] = essay_settings['max_words']
        try:
            parsed = [_question_fields_from_payload(fields) for fields in parsed]
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        batch_id = request.data.get('batch_id')
        if batch_id not in (None, ''):
            try:
                batch = _bank_batch_for_manual_question(subject, {'batch_id': batch_id})
            except ValueError as exc:
                return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            batch_name = str(request.data.get('batch_name') or 'Question import').strip()[:160]
            if not batch_name:
                return Response({'error': 'Batch name is required.'}, status=status.HTTP_400_BAD_REQUEST)
            batch = QuestionBankBatch.objects.create(subject=subject, name=batch_name)
        items = QuestionBankItem.objects.bulk_create([
            QuestionBankItem(subject=subject, batch=batch, **fields) for fields in parsed
        ])
        return Response({'created_count': len(items), 'batch': _serialize_bank_batch(batch)}, status=status.HTTP_201_CREATED)

    try:
        question_fields = _question_fields_from_payload(request.data)
    except ValueError as exc:
        return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    try:
        batch = _bank_batch_for_manual_question(subject, request.data)
    except ValueError as exc:
        return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    item = QuestionBankItem.objects.create(subject=subject, batch=batch, **question_fields)
    return Response(_serialize_bank_item(item), status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def subject_question_bank_detail(request, subject_id, question_id):
    if not _is_instructor(request.user):
        return Response({'error': 'Instructor access required.'}, status=status.HTTP_403_FORBIDDEN)
    subject = Subject.objects.filter(
        Q(instructor=request.user) | Q(additional_instructors=request.user), id=subject_id,
    ).distinct().first()
    if not subject:
        return Response({'error': 'Subject not found.'}, status=status.HTTP_404_NOT_FOUND)
    item = QuestionBankItem.objects.filter(subject=subject, id=question_id).first()
    if not item:
        return Response({'error': 'Question not found.'}, status=status.HTTP_404_NOT_FOUND)
    batch = item.batch
    item.delete()
    if batch and not batch.questions.exists():
        batch.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def subject_question_bank_batch_detail(request, subject_id, batch_id):
    if not _is_instructor(request.user):
        return Response({'error': 'Instructor access required.'}, status=status.HTTP_403_FORBIDDEN)
    subject = Subject.objects.filter(
        Q(instructor=request.user) | Q(additional_instructors=request.user), id=subject_id,
    ).distinct().first()
    if not subject:
        return Response({'error': 'Subject not found.'}, status=status.HTTP_404_NOT_FOUND)
    batch = QuestionBankBatch.objects.filter(subject=subject, id=batch_id).first()
    if not batch:
        return Response({'error': 'Question batch not found.'}, status=status.HTTP_404_NOT_FOUND)
    batch.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def exam_add_bank_questions(request, subject_id, exam_set_id):
    """Copy selected bank questions into a draft exam in the chosen order."""
    if not _is_instructor(request.user):
        return Response({'error': 'Instructor access required.'}, status=status.HTTP_403_FORBIDDEN)
    subject = Subject.objects.filter(
        Q(instructor=request.user) | Q(additional_instructors=request.user), id=subject_id,
    ).distinct().first()
    if not subject:
        return Response({'error': 'Subject not found.'}, status=status.HTTP_404_NOT_FOUND)
    ids_raw = request.data.get('question_ids')
    if not isinstance(ids_raw, list) or not 1 <= len(ids_raw) <= 500:
        return Response({'error': 'Select between 1 and 500 bank questions.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        ids = [int(value) for value in ids_raw]
    except (TypeError, ValueError):
        return Response({'error': 'Invalid question selection.'}, status=status.HTTP_400_BAD_REQUEST)
    if len(set(ids)) != len(ids):
        return Response({'error': 'Duplicate questions in selection.'}, status=status.HTTP_400_BAD_REQUEST)
    bank_items = {item.id: item for item in QuestionBankItem.objects.filter(subject=subject, id__in=ids)}
    if len(bank_items) != len(ids):
        return Response({'error': 'One or more questions are outside this course.'}, status=status.HTTP_400_BAD_REQUEST)
    with transaction.atomic():
        exam_set = ExamSet.objects.select_for_update().filter(id=exam_set_id, subject=subject).first()
        if not exam_set:
            return Response({'error': 'Exam not found.'}, status=status.HTTP_404_NOT_FOUND)
        if exam_set.is_final:
            return Response({'error': 'Published exams cannot be altered.'}, status=status.HTTP_403_FORBIDDEN)
        existing_ids = set(ExamQuestion.objects.filter(exam_set=exam_set, bank_item_id__in=ids).values_list('bank_item_id', flat=True))
        last_order = ExamQuestion.objects.filter(exam_set=exam_set).order_by('-order').values_list('order', flat=True).first() or 0
        copies = []
        for item_id in ids:
            if item_id in existing_ids:
                continue
            item = bank_items[item_id]
            last_order += 1
            copies.append(ExamQuestion(
                exam_set=exam_set, bank_item=item, order=last_order,
                question_type=item.question_type, question_text=item.question_text,
                choices=item.choices, correct_answer=item.correct_answer,
                points=item.points, max_words=item.max_words, case_sensitive=item.case_sensitive,
            ))
        ExamQuestion.objects.bulk_create(copies)
        if any(question.question_type != ExamQuestion.TYPE_ESSAY for question in copies):
            _enable_all_proctoring_restrictions(exam_set)
    return Response({'added_count': len(copies)}, status=status.HTTP_201_CREATED)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def exam_questions(request, subject_id, exam_set_id):
    """Instructor: list or create questions for an exam set."""
    if not _is_instructor(request.user):
        return Response({'error': 'Instructor access required.'}, status=status.HTTP_403_FORBIDDEN)

    subject = Subject.objects.filter(Q(instructor=request.user) | Q(additional_instructors=request.user), id=subject_id).distinct().first()
    if not subject:
        return Response({'error': 'Subject not found.'}, status=status.HTTP_404_NOT_FOUND)

    exam_set = ExamSet.objects.filter(id=exam_set_id, subject=subject).first()
    if not exam_set:
        return Response({'error': 'Exam set not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        qs = ExamQuestion.objects.filter(exam_set=exam_set)
        if _exam_requires_all_restrictions(exam_set):
            _enable_all_proctoring_restrictions(exam_set)
        return Response(
            {
                'is_final': exam_set.is_final,
                'proctoring_restrictions': _serialize_proctoring_restrictions(exam_set),
                'requires_all_restrictions': _exam_requires_all_restrictions(exam_set),
                'questions': [_serialize_question(q) for q in qs]
            },
            status=status.HTTP_200_OK,
        )

    if exam_set.is_final:
        return Response({'error': 'Exam is final and cannot be altered.'}, status=status.HTTP_403_FORBIDDEN)

    # Keep legacy direct creation working while also making it reusable.
    try:
        question_fields = _question_fields_from_payload(request.data)
    except ValueError as exc:
        return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    # Auto-assign order = next integer
    last_order = (
        ExamQuestion.objects.filter(exam_set=exam_set).order_by('-order').values_list('order', flat=True).first()
    )
    order = (last_order or 0) + 1

    with transaction.atomic():
        batch = _bank_batch_for_manual_question(subject, {'batch_name': f'{exam_set.title} questions'})
        bank_item = QuestionBankItem.objects.create(subject=subject, batch=batch, **question_fields)
        q = ExamQuestion.objects.create(exam_set=exam_set, order=order, bank_item=bank_item, **question_fields)
    if q.question_type != ExamQuestion.TYPE_ESSAY:
        _enable_all_proctoring_restrictions(exam_set)
    return Response(_serialize_question(q), status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def exam_question_detail(request, subject_id, exam_set_id, question_id):
    """Instructor: delete a single question."""
    if not _is_instructor(request.user):
        return Response({'error': 'Instructor access required.'}, status=status.HTTP_403_FORBIDDEN)

    subject = Subject.objects.filter(Q(instructor=request.user) | Q(additional_instructors=request.user), id=subject_id).distinct().first()
    if not subject:
        return Response({'error': 'Subject not found.'}, status=status.HTTP_404_NOT_FOUND)

    q = ExamQuestion.objects.filter(
        id=question_id,
        exam_set_id=exam_set_id,
        exam_set__subject=subject,
    ).first()
    if not q:
        return Response({'error': 'Question not found.'}, status=status.HTTP_404_NOT_FOUND)
    
    if q.exam_set.is_final:
        return Response({'error': 'Exam is final and cannot be altered.'}, status=status.HTTP_403_FORBIDDEN)

    q.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def finalize_exam(request, subject_id, exam_set_id):
    """Instructor: Finalize an exam. Once finalized, no questions can be altered."""
    if not _is_instructor(request.user):
        return Response({'error': 'Instructor access required.'}, status=status.HTTP_403_FORBIDDEN)

    subject = Subject.objects.filter(Q(instructor=request.user) | Q(additional_instructors=request.user), id=subject_id).distinct().first()
    if not subject:
        return Response({'error': 'Subject not found.'}, status=status.HTTP_404_NOT_FOUND)

    exam_set = ExamSet.objects.filter(id=exam_set_id, subject=subject).first()
    if not exam_set:
        return Response({'error': 'Exam set not found.'}, status=status.HTTP_404_NOT_FOUND)

    if not exam_set.is_final:
        if _exam_requires_all_restrictions(exam_set):
            _enable_all_proctoring_restrictions(exam_set)
        exam_set.is_final = True
        exam_set.save(update_fields=['is_final'])
        transaction.on_commit(lambda: notify_exam_published(subject.id))
    
    return Response({'message': 'Exam finalized successfully.'}, status=status.HTTP_200_OK)

# ---------------------------------------------------------------------------
# STUDENT – Exam taking endpoints
# ---------------------------------------------------------------------------

def _student_can_access_exam(student_email, exam_set):
    """Return True if the student is enrolled in a set linked to the exam's subject and assigned sets."""
    assigned_sets = exam_set.assigned_sets.all()
    allowed_qs = EnrolledStudent.objects.filter(
        email__iexact=student_email,
        student_set__subject_id=exam_set.subject_id,
    )
    # Check assignments and enrollment in one query. This path runs on every
    # live gadget frame, so an extra remote DB round trip is visible to users.
    return allowed_qs.filter(
        Q(student_set__in=assigned_sets) | ~Exists(assigned_sets),
    ).exists()


def _student_question_choices(question, submission):
    """Keep each attempt's choice order stable without changing stored answers."""
    choices = question.choices or []
    if question.question_type != ExamQuestion.TYPE_MULTIPLE_CHOICE:
        return choices
    return [choice for _, choice in sorted(
        enumerate(choices),
        key=lambda indexed_choice: salted_hmac(
            'student-exam-choice-order',
            f'{submission.pk}:{submission.attempt_count}:{question.pk}:{indexed_choice[0]}',
            algorithm='sha256',
        ).digest(),
    )]


def _student_ordered_questions(exam_set, submission):
    return sorted(
        ExamQuestion.objects.filter(exam_set=exam_set),
        key=lambda question: (
            question.question_type == ExamQuestion.TYPE_ESSAY,
            salted_hmac(
                'student-exam-question-order',
                f'{submission.pk}:{submission.attempt_count}:{question.pk}',
                algorithm='sha256',
            ).digest(),
        ),
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_exam_questions(request, exam_id):
    """Student: fetch all questions for an exam (without correct_answer)."""
    exam_set = ExamSet.objects.select_related('subject').filter(id=exam_id).first()
    if not exam_set:
        return Response({'error': 'Exam not found.'}, status=status.HTTP_404_NOT_FOUND)

    if not _student_can_access_exam(request.user.email, exam_set):
        return Response({'error': 'You are not enrolled in this exam.'}, status=status.HTTP_403_FORBIDDEN)

    if not exam_set.is_final:
        return Response({'error': 'This exam is not published yet.'}, status=status.HTTP_403_FORBIDDEN)
        
    now = timezone.now()
    if exam_set.available_from and now < exam_set.available_from:
        return Response({'error': 'Exam is not yet open.'}, status=status.HTTP_403_FORBIDDEN)
    if exam_set.due_at and now > exam_set.due_at:
        return Response({'error': 'Exam is closed and cannot be taken.'}, status=status.HTTP_403_FORBIDDEN)

    # Handle tracking of submission/attempts
    from .gaze_service import selected_gaze_model_code
    submission, created = ExamSubmission.objects.get_or_create(
        exam_set=exam_set,
        student_email=request.user.email.lower(),
        defaults={'started_at': now, 'gaze_model_code': selected_gaze_model_code()}
    )
    if not created:
        if submission.is_done:
            # Check attempt limit
            if submission.attempt_count >= exam_set.max_attempts:
                return Response({'error': 'You have reached the maximum number of attempts for this exam.'}, status=status.HTTP_403_FORBIDDEN)
            # Reset submission for a new attempt
            submission.is_done = False
            submission.score = None
            submission.integrity_score = None
            submission.terminated = False
            submission.attempt_count += 1
            submission.started_at = now
            submission.gaze_model_code = selected_gaze_model_code()
            submission.submitted_at = None
            submission.question_index = 0
            submission.locked_answers = {}
            submission.iris_verified_at = None
            submission.gaze_glance_count = 0
            submission.gaze_glance_last_frame_hash = ''
            submission.save()
            _clear_proctoring_for_attempt(submission)
            # Clear gaze smoother state for the new attempt
            from .gaze_service import reset_submission_state
            reset_submission_state(submission.id)
            # Clear previous answers
            StudentAnswer.objects.filter(exam_set=exam_set, student_email=request.user.email.lower()).delete()
        elif not submission.started_at:
            submission.started_at = now
            submission.gaze_model_code = selected_gaze_model_code()
            submission.save(update_fields=['started_at', 'gaze_model_code'])

    if not submission.is_done:
        already_started = ExamProctoringEvent.objects.filter(
            submission=submission,
            attempt_number=submission.attempt_count,
            event_type=ExamProctoringEvent.EVENT_EXAM_STARTED,
        ).exists()
        if not already_started:
            _log_proctoring_event(
                submission,
                ExamProctoringEvent.EVENT_EXAM_STARTED,
                severity=ExamProctoringEvent.SEVERITY_INFO,
                message='Student opened the exam.',
                source='questions',
            )

    # A stable pseudorandom rank gives each student/attempt its own sequence,
    # including across refreshes and server restarts. Keep stored question IDs
    # and instructor ordering intact so answers continue to grade by ID.
    qs = _student_ordered_questions(exam_set, submission)
    questions = [
        {
            **_serialize_question(q, include_answer=False),
            'order': position,
            'choices': _student_question_choices(q, submission),
        }
        for position, q in enumerate(qs, start=1)
    ]
    if _exam_requires_all_restrictions(exam_set):
        _enable_all_proctoring_restrictions(exam_set)
    return Response({
        'questions': questions,
        'started_at': submission.started_at,
        'time_limit': exam_set.time_limit,
        'allow_backtracking': exam_set.allow_backtracking,
        'question_index': min(submission.question_index, max(len(qs) - 1, 0)),
        'locked_answers': submission.locked_answers if not exam_set.allow_backtracking else {},
        'gaze_glance_count': submission.gaze_glance_count,
        'gaze_glance_threshold': _gaze_glances_per_violation(exam_set),
        'proctoring_restrictions': _serialize_proctoring_restrictions(exam_set),
    }, status=status.HTTP_200_OK)


def _iris_check_current(submission, exam_set, now):
    """Allow a verified eye image or a server-confirmed expired exam timer."""
    if submission.started_at and exam_set.time_limit and now >= submission.started_at + timedelta(minutes=exam_set.time_limit):
        return True
    return bool(submission.iris_verified_at and now - submission.iris_verified_at <= timedelta(seconds=10))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def student_advance_question(request, exam_id):
    """Lock the current answer before advancing in a one-way exam."""
    exam_set = ExamSet.objects.filter(id=exam_id).first()
    if not exam_set:
        return Response({'error': 'Exam not found.'}, status=status.HTTP_404_NOT_FOUND)
    if not _student_can_access_exam(request.user.email, exam_set):
        return Response({'error': 'You are not enrolled in this exam.'}, status=status.HTTP_403_FORBIDDEN)
    if not exam_set.is_final or exam_set.allow_backtracking:
        return Response({'error': 'This exam does not use one-way navigation.'}, status=status.HTTP_400_BAD_REQUEST)
    now = timezone.now()
    if (exam_set.available_from and now < exam_set.available_from) or (exam_set.due_at and now > exam_set.due_at):
        return Response({'error': 'This exam is not open.'}, status=status.HTTP_403_FORBIDDEN)
    with transaction.atomic():
        submission = ExamSubmission.objects.select_for_update().filter(
            exam_set=exam_set, student_email=request.user.email.lower(), is_done=False,
        ).first()
        if not submission:
            return Response({'error': 'Start the exam before advancing.'}, status=status.HTTP_409_CONFLICT)
        if not _iris_check_current(submission, exam_set, now):
            return Response({'error': 'Your irises are not clearly visible. Remove dark glasses, or adjust prescription glasses and lighting, then look at the camera.'}, status=status.HTTP_409_CONFLICT)
        questions = _student_ordered_questions(exam_set, submission)
        index = submission.question_index
        if index >= len(questions) - 1:
            return Response({'error': 'This is the last question.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            question_id = int(request.data.get('question_id'))
        except (TypeError, ValueError):
            return Response({'error': 'Invalid question.'}, status=status.HTTP_400_BAD_REQUEST)
        if question_id != questions[index].id:
            return Response({'error': 'Question position changed. Reload the exam to continue.'}, status=status.HTTP_409_CONFLICT)
        answer_text = str(request.data.get('answer_text') or '').strip()
        question = questions[index]
        if question.question_type == ExamQuestion.TYPE_ESSAY and question.max_words and len(answer_text.split()) > question.max_words:
            return Response(
                {'error': f'Essay answer exceeds the {question.max_words}-word limit.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        locked = dict(submission.locked_answers or {})
        locked[str(question_id)] = answer_text
        submission.locked_answers = locked
        submission.question_index = index + 1
        submission.save(update_fields=['locked_answers', 'question_index', 'updated_at'])
    return Response({'question_index': index + 1}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def student_submit_answers(request, exam_id):
    """
    Student: submit answers for an exam.

    Expects JSON body:
        { "answers": [ { "question_id": <int>, "answer_text": "<str>" }, ... ] }

    - MC, identification, and enumeration are auto-graded when a correct answer exists.
    - Essay answers: is_correct = None (manual later).
    - After grading, sets ExamSubmission.is_done=True and stores score.
    """
    exam_set = ExamSet.objects.select_related('subject').filter(id=exam_id).first()
    if not exam_set:
        return Response({'error': 'Exam not found.'}, status=status.HTTP_404_NOT_FOUND)

    student_email = request.user.email.lower()

    if not _student_can_access_exam(student_email, exam_set):
        return Response({'error': 'You are not enrolled in this exam.'}, status=status.HTTP_403_FORBIDDEN)

    if not exam_set.is_final:
        return Response({'error': 'This exam is not published yet.'}, status=status.HTTP_403_FORBIDDEN)
        
    now = timezone.now()
    if exam_set.available_from and now < exam_set.available_from:
        return Response({'error': 'Exam is not yet open.'}, status=status.HTTP_403_FORBIDDEN)
    if exam_set.due_at and now > exam_set.due_at:
        return Response({'error': 'Exam is closed and cannot be taken.'}, status=status.HTTP_403_FORBIDDEN)

    # Block if max attempts reached and currently done
    existing = ExamSubmission.objects.filter(exam_set=exam_set, student_email=student_email).first()
    if existing and existing.is_done:
        if existing.attempt_count >= exam_set.max_attempts:
            return Response(
                {'error': 'You have already submitted this exam and exhausted all attempts.', 'already_submitted': True},
                status=status.HTTP_409_CONFLICT,
            )
        else:
            return Response(
                {'error': 'You must start a new attempt before submitting.', 'already_submitted': True},
                status=status.HTTP_409_CONFLICT,
            )

    answers_payload = request.data.get('answers')
    terminated = bool(request.data.get('terminated', False))
    tab_switches = int(request.data.get('tab_switches', 0))
    browser_warning_count = int(request.data.get('browser_warning_count', tab_switches))
    gaze_violations = int(request.data.get('gaze_violations', 0))
    gaze_no_face = int(request.data.get('gaze_no_face', 0))
    termination_reason = (request.data.get('termination_reason') or '').strip()

    if not terminated and not existing:
        return Response({'error': 'Start the exam before submitting.'}, status=status.HTTP_409_CONFLICT)
    if not terminated and not _iris_check_current(existing, exam_set, now):
        return Response({'error': 'Your irises are not clearly visible. Remove dark glasses, or adjust prescription glasses and lighting, then look at the camera.'}, status=status.HTTP_409_CONFLICT)

    # Allow submission with no answers when terminated (system force-submitting)
    if not terminated:
        if not isinstance(answers_payload, list) or not answers_payload:
            return Response({'error': '"answers" list is required.'}, status=status.HTTP_400_BAD_REQUEST)
    elif not isinstance(answers_payload, list):
        answers_payload = []

    questions = {q.id: q for q in ExamQuestion.objects.filter(exam_set=exam_set)}

    saved_answers = []
    auto_total = 0.0
    auto_correct = 0.0
    answered_map = {}
    for item in (answers_payload or []):
        q_id = item.get('question_id')
        if q_id is None:
            continue
        try:
            answered_map[int(q_id)] = str(item.get('answer_text') or '').strip()
        except (TypeError, ValueError):
            continue

    if not exam_set.allow_backtracking:
        if not existing:
            return Response({'error': 'Start the exam before submitting.'}, status=status.HTTP_409_CONFLICT)
        ordered_questions = _student_ordered_questions(exam_set, existing)
        locked = existing.locked_answers or {}
        for index, question in enumerate(ordered_questions):
            if index < existing.question_index:
                answered_map[question.id] = str(locked.get(str(question.id), ''))
            elif index > existing.question_index:
                answered_map[question.id] = ''

    if not terminated:
        for question in questions.values():
            if question.question_type == ExamQuestion.TYPE_ESSAY and question.max_words and len(answered_map.get(question.id, '').split()) > question.max_words:
                return Response(
                    {'error': f'Essay answer exceeds the {question.max_words}-word limit.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

    for q in questions.values():
        answer_text = answered_map.get(q.id, '')
        is_correct, credit = grade_question(q, answer_text)
        if is_correct is not None:
            auto_total += 1.0
            auto_correct += float(credit)

        # Upsert the student answer.
        # IMPORTANT: update_or_create only writes `defaults` when CREATING a new row,
        # not when updating an existing one. If a StudentAnswer already exists from a
        # prior partial save, is_correct would be left stale. We force-write it here.
        obj, created = StudentAnswer.objects.update_or_create(
            exam_set=exam_set,
            question=q,
            student_email=student_email,
            defaults={'answer_text': answer_text, 'is_correct': is_correct},
        )
        if not created:
            obj.answer_text = answer_text
            obj.is_correct = is_correct
            obj.save(update_fields=['answer_text', 'is_correct'])
        saved_answers.append(obj)

    mc_total = int(auto_total)
    mc_correct = round(auto_correct, 2)
    mc_score = round((auto_correct / auto_total) * 100, 2) if auto_total > 0 else None

    now_ts = timezone.now()
    updated = ExamSubmission.objects.filter(
        exam_set=exam_set,
        student_email=student_email,
        is_done=False,
    ).update(
        is_done=True,
        score=mc_score,
        submitted_at=now_ts,
        terminated=terminated,
        tab_switches=tab_switches,
    )
    if updated:
        submission = ExamSubmission.objects.filter(
            exam_set=exam_set, student_email=student_email,
        ).first()
    else:
        submission, _ = ExamSubmission.objects.update_or_create(
            exam_set=exam_set,
            student_email=student_email,
            defaults={
                'is_done': True,
                'score': mc_score,
                'submitted_at': now_ts,
                'terminated': terminated,
                'tab_switches': tab_switches,
            },
        )

    end_event = (
        ExamProctoringEvent.EVENT_EXAM_TERMINATED
        if terminated
        else ExamProctoringEvent.EVENT_EXAM_SUBMITTED
    )
    end_message = 'Exam ended by student submission.'
    if terminated and termination_reason == 'gaze':
        end_message = (
            f'Exam auto-terminated: gaze violations ({gaze_violations}), '
            f'face not visible ({gaze_no_face}).'
        )
    elif terminated and termination_reason == 'screen_share':
        end_message = 'Exam auto-terminated because entire-screen sharing stopped.'
    elif terminated and termination_reason == 'split_screen':
        end_message = f'Exam auto-terminated after {browser_warning_count} browser warnings; split-screen or window resizing was detected.'
    elif terminated and termination_reason == 'extended_monitor':
        end_message = f'Exam auto-terminated after {browser_warning_count} browser warnings; an additional display was detected.'
    elif terminated and termination_reason == 'screenshot':
        end_message = f'Exam auto-terminated after {browser_warning_count} browser warnings; a screenshot shortcut was attempted.'
    elif terminated:
        end_message = f'Exam auto-terminated after {browser_warning_count} browser warnings (tab or window departures: {tab_switches}).'

    _log_proctoring_event(
        submission,
        end_event,
        severity=ExamProctoringEvent.SEVERITY_CRITICAL if terminated else ExamProctoringEvent.SEVERITY_INFO,
        message=end_message,
        source='submit',
        metadata={
            'tab_switches': tab_switches,
            'browser_warning_count': browser_warning_count,
            'gaze_violations': gaze_violations,
            'gaze_no_face': gaze_no_face,
            'termination_reason': termination_reason,
            'mc_score': float(mc_score) if mc_score is not None else None,
        },
    )
    integrity_report = _build_integrity_report(submission)

    return Response(
        {
            'submitted': True,
            'terminated': terminated,
            'tab_switches': tab_switches,
            'mc_total': mc_total,
            'mc_correct': mc_correct,
            'mc_score': mc_score,
            'submission_id': submission.id,
            'integrity_score': float(integrity_report.integrity_score),
            'started_at': submission.started_at,
            'submitted_at': submission.submitted_at,
        },
        status=status.HTTP_200_OK,
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_my_answers(request, exam_id):
    """Student: view their previously submitted answers and score."""
    exam_set = ExamSet.objects.select_related('subject').filter(id=exam_id).first()
    if not exam_set:
        return Response({'error': 'Exam not found.'}, status=status.HTTP_404_NOT_FOUND)

    student_email = request.user.email.lower()

    if not _student_can_access_exam(student_email, exam_set):
        return Response({'error': 'You are not enrolled in this exam.'}, status=status.HTTP_403_FORBIDDEN)

    submission = ExamSubmission.objects.filter(exam_set=exam_set, student_email=student_email).first()
    if not submission or not submission.is_done:
        return Response({'submitted': False}, status=status.HTTP_200_OK)

    answers = StudentAnswer.objects.filter(
        exam_set=exam_set,
        student_email=student_email,
    ).select_related('question')

    answer_list = []
    for a in answers:
        answer_list.append({
            'question_id': a.question_id,
            'question_text': a.question.question_text,
            'question_type': a.question.question_type,
            'choices': a.question.choices or [],
            'answer_text': a.answer_text,
            'is_correct': a.is_correct,
            'correct_answer': (
                a.question.correct_answer
                if a.question.question_type in (
                    ExamQuestion.TYPE_MULTIPLE_CHOICE,
                    ExamQuestion.TYPE_IDENTIFICATION,
                    ExamQuestion.TYPE_ENUMERATION,
                )
                else None
            ),
        })

    auto_answers = [
        a for a in answers
        if a.is_correct is not None
        and a.question.question_type in (
            ExamQuestion.TYPE_MULTIPLE_CHOICE,
            ExamQuestion.TYPE_IDENTIFICATION,
            ExamQuestion.TYPE_ENUMERATION,
        )
    ]
    mc_total = len(auto_answers)
    mc_correct = sum(1 for a in auto_answers if a.is_correct)

    report = ExamIntegrityReport.objects.filter(
        submission=submission,
        attempt_number=submission.attempt_count,
    ).first()

    return Response(
        {
            'submitted': True,
            'mc_total': mc_total,
            'mc_correct': mc_correct,
            'mc_score': float(submission.score) if submission.score is not None else None,
            'integrity_score': float(submission.integrity_score) if submission.integrity_score is not None else None,
            'integrity_report_id': report.id if report else None,
            'started_at': submission.started_at,
            'submitted_at': submission.submitted_at,
            'terminated': submission.terminated,
            'tab_switches': submission.tab_switches,
            'answers': answer_list,
        },
        status=status.HTTP_200_OK,
    )


# ---------------------------------------------------------------------------
# Proctoring — events, evidence, integrity reports
# ---------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def student_log_proctoring_events(request, exam_id):
    """Student: log one or more proctoring events during an active exam attempt."""
    exam_set = ExamSet.objects.filter(id=exam_id).first()
    if not exam_set:
        return Response({'error': 'Exam not found.'}, status=status.HTTP_404_NOT_FOUND)

    student_email = request.user.email.lower()
    if not _student_can_access_exam(student_email, exam_set):
        return Response({'error': 'You are not enrolled in this exam.'}, status=status.HTTP_403_FORBIDDEN)

    submission, created = ExamSubmission.objects.get_or_create(
        exam_set=exam_set,
        student_email=student_email,
        defaults={'started_at': timezone.now()},
    )
    if submission.is_done:
        return Response({'error': 'No active exam attempt.'}, status=status.HTTP_400_BAD_REQUEST)
    if created or not submission.started_at:
        submission.started_at = submission.started_at or timezone.now()
        update_fields = ['started_at']
        if created:
            from .gaze_service import selected_gaze_model_code
            submission.gaze_model_code = selected_gaze_model_code()
            update_fields.append('gaze_model_code')
        submission.save(update_fields=update_fields)

    events_payload = request.data.get('events')
    if not isinstance(events_payload, list) or not events_payload:
        single = request.data
        events_payload = [single] if single.get('event_type') else []

    if not events_payload:
        return Response({'error': '"events" list or event_type is required.'}, status=status.HTTP_400_BAD_REQUEST)

    allowed_types = {c[0] for c in ExamProctoringEvent.EVENT_TYPES}
    created = []
    for item in events_payload:
        event_type = (item.get('event_type') or '').strip()
        if event_type not in allowed_types:
            continue
        event = _log_proctoring_event(
            submission,
            event_type,
            severity=item.get('severity') or None,
            message=(item.get('message') or '').strip(),
            source=(item.get('source') or '').strip(),
            metadata=item.get('metadata') if isinstance(item.get('metadata'), dict) else {},
        )
        created.append(_serialize_proctoring_event(event))

    return Response({'logged': len(created), 'events': created}, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def student_upload_proctoring_evidence(request, exam_id):
    """Student: upload webcam/screen screenshot as integrity evidence."""
    exam_set = ExamSet.objects.filter(id=exam_id).first()
    if not exam_set:
        return Response({'error': 'Exam not found.'}, status=status.HTTP_404_NOT_FOUND)

    student_email = request.user.email.lower()
    if not _student_can_access_exam(student_email, exam_set):
        return Response({'error': 'You are not enrolled in this exam.'}, status=status.HTTP_403_FORBIDDEN)

    submission, created = ExamSubmission.objects.get_or_create(
        exam_set=exam_set,
        student_email=student_email,
        defaults={'started_at': timezone.now()},
    )
    if submission.is_done:
        return Response({'error': 'No active exam attempt.'}, status=status.HTTP_400_BAD_REQUEST)
    if created or not submission.started_at:
        submission.started_at = submission.started_at or timezone.now()
        update_fields = ['started_at']
        if created:
            from .gaze_service import selected_gaze_model_code
            submission.gaze_model_code = selected_gaze_model_code()
            update_fields.append('gaze_model_code')
        submission.save(update_fields=update_fields)

    image = request.FILES.get('image')
    if not image:
        return Response({'error': 'image file is required.'}, status=status.HTTP_400_BAD_REQUEST)

    evidence_type = (request.data.get('evidence_type') or ExamProctoringEvidence.TYPE_WEBCAM).strip()
    if evidence_type not in {c[0] for c in ExamProctoringEvidence.EVIDENCE_TYPES}:
        evidence_type = ExamProctoringEvidence.TYPE_WEBCAM

    caption = (request.data.get('caption') or '').strip()
    event_id = request.data.get('event_id')
    linked_event = None
    if event_id:
        linked_event = ExamProctoringEvent.objects.filter(
            id=event_id,
            submission=submission,
            attempt_number=submission.attempt_count,
        ).first()

    evidence = ExamProctoringEvidence.objects.create(
        submission=submission,
        attempt_number=submission.attempt_count,
        event=linked_event,
        evidence_type=evidence_type,
        image=image,
        caption=caption,
    )

    return Response(
        _serialize_proctoring_evidence(evidence, request),
        status=status.HTTP_201_CREATED,
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def student_analyze_gaze(request, exam_id):
    """Student: analyze a webcam frame for gaze direction (AI proctoring)."""
    exam_set = ExamSet.objects.filter(id=exam_id).first()
    if not exam_set:
        return Response({'error': 'Exam not found.'}, status=status.HTTP_404_NOT_FOUND)

    student_email = request.user.email.lower()
    if not _student_can_access_exam(student_email, exam_set):
        return Response({'error': 'You are not enrolled in this exam.'}, status=status.HTTP_403_FORBIDDEN)

    submission, created = ExamSubmission.objects.get_or_create(
        exam_set=exam_set,
        student_email=student_email,
        defaults={'started_at': timezone.now()},
    )
    if submission.is_done:
        return Response({'error': 'No active exam attempt.'}, status=status.HTTP_400_BAD_REQUEST)
    if created or not submission.started_at:
        submission.started_at = submission.started_at or timezone.now()
        update_fields = ['started_at']
        if created:
            from .gaze_service import selected_gaze_model_code
            submission.gaze_model_code = selected_gaze_model_code()
            update_fields.append('gaze_model_code')
        submission.save(update_fields=update_fields)

    image = request.FILES.get('image')
    if not image:
        return Response({'error': 'image file is required.'}, status=status.HTTP_400_BAD_REQUEST)

    from django.core import signing
    from .gaze_service import analyze_frame_bytes, read_gaze_result, schedule_live_snapshot

    raw = image.read()
    receipt = request.data.get('frame_receipt')
    try:
        if receipt:
            # Reuse the server's signed WS result for this exact JPEG. No second
            # model run and no live-preview upload before recording evidence.
            result = read_gaze_result(receipt, exam_id, student_email, raw)
        else:
            result = analyze_frame_bytes(raw)
            schedule_live_snapshot(exam_id, student_email, raw)
    except signing.BadSignature:
        return Response({'error': 'Gaze frame receipt is invalid or expired.'}, status=400)
    except ValueError:
        return Response({'error': 'Could not decode image.'}, status=400)
    except Exception as exc:
        return Response({'error': f'Gaze model unavailable: {exc}'}, status=503)

    payload = result.to_dict()
    if result.iris_visible and (
        not submission.iris_verified_at or timezone.now() - submission.iris_verified_at >= timedelta(seconds=3)
    ):
        submission.iris_verified_at = timezone.now()
        submission.save(update_fields=['iris_verified_at', 'updated_at'])
    payload['confidence_threshold'] = GAZE_CONFIDENCE_THRESHOLD
    payload['above_confidence_threshold'] = GAZE_ABOVE_CONFIDENCE_THRESHOLD
    payload['left_confidence_threshold'] = GAZE_LEFT_CONFIDENCE_THRESHOLD
    payload['right_confidence_threshold'] = GAZE_RIGHT_CONFIDENCE_THRESHOLD
    payload['below_confidence_threshold'] = GAZE_BELOW_CONFIDENCE_THRESHOLD
    payload['left_right_continuous_seconds'] = GAZE_LEFT_RIGHT_CONTINUOUS_SECONDS
    payload['above_continuous_seconds'] = GAZE_ABOVE_CONTINUOUS_SECONDS
    payload['below_continuous_seconds'] = GAZE_BELOW_CONTINUOUS_SECONDS
    payload['no_face_hold_seconds'] = GAZE_NO_FACE_HOLD_SECONDS
    payload['check_interval_seconds'] = GAZE_CONTINUOUS_SECONDS
    payload['continuous_seconds_required'] = GAZE_CONTINUOUS_SECONDS

    record_strike = str(request.data.get('record_strike', 'false')).lower() in ('1', 'true', 'yes')
    record_glance = str(request.data.get('record_glance', 'false')).lower() in ('1', 'true', 'yes')
    if record_glance and not receipt:
        return Response({'error': 'A signed gaze frame is required for a glance count.'}, status=status.HTTP_400_BAD_REQUEST)
    forced_label = _resolve_forced_gaze_label(
        request.data.get('forced_label', '').strip(),
        [result.label],
    )
    logged_event = None
    is_no_face = not result.face_detected or result.label in ('no_face', 'multiple_people')
    question_id = request.data.get('question_id')
    direction_enabled = _gaze_direction_enabled(exam_set, result.label, question_id)
    if not direction_enabled:
        forced_label = None
        payload['is_suspicious'] = False
        payload['is_normal'] = True
    payload['direction_enabled'] = direction_enabled
    glance_direction = _high_confidence_gaze_direction(result, direction_enabled) if not is_no_face else ''
    glance_threshold = _gaze_glances_per_violation(exam_set)
    glance_counted = False
    glance_completed = False
    if record_glance or (not receipt and not record_strike):
        if _new_gaze_glance_episode(submission, glance_direction, from_websocket=record_glance):
            glance_counted, glance_completed = _increment_gaze_glance_count(submission, raw, glance_threshold)
    elif not record_strike and not glance_direction:
        _new_gaze_glance_episode(submission, '', from_websocket=False)
    payload['gaze_glance_count'] = submission.gaze_glance_count
    payload['gaze_glance_threshold'] = glance_threshold
    payload['glance_counted'] = glance_counted
    payload['glance_violation'] = glance_completed
    gaze_conf_ok = direction_enabled and result.is_suspicious and _gaze_violation_confidence_ok(
        result.label, result.confidence
    )

    absence_info = _process_no_face_absence(submission, is_no_face)
    payload['hold_exam'] = absence_info['hold_exam']
    payload['absent_seconds'] = round(absence_info['absent_seconds'], 1)

    now_dt = timezone.now()
    is_normal_label = 'normal' in result.label.lower()
    should_log = False

    # The WS timer requests a strike using a server-verified frame result.
    # Preserve its real confidence and label in the evidence metadata.
    if record_glance:
        pass  # The signed frame is used only for the shared short-gaze tally.
    elif record_strike and forced_label and gaze_conf_ok and not is_no_face:
        _gaze_mark_suspicious(submission, now_dt)
        _clear_gaze_pending(submission)
        should_log = not _gaze_in_violation_cooldown(submission, now_dt)
    elif is_no_face:
        _clear_gaze_pending(submission)
        should_log = absence_info['should_log_strike']
    elif gaze_conf_ok and not (receipt and request.data.get('observe_only') == 'true'):
        _gaze_mark_suspicious(submission, now_dt)
        # HTTP fallback: if WebSocket never records the strike, still log after
        # the continuous look-away window. Cooldown prevents double-counting
        # with the WS path.
        if not _gaze_in_violation_cooldown(submission, now_dt):
            should_log = _gaze_continuous_strike_ready(submission, result.label)
    elif is_normal_label or not result.is_suspicious:
        # Only clear the timer after 1.5s of continuous normal frames.
        # A single flickering normal result must not reset the continuous timer.
        if _gaze_normal_long_enough(submission, now_dt, grace_seconds=0.35):
            _clear_gaze_pending(submission)
    # else: suspicious but low-confidence uncertain frame — keep the timer running

    gaze_meta = _gaze_event_metadata(
        result,
        hold_exam=absence_info['hold_exam'],
        absent_seconds=round(absence_info['absent_seconds'], 1),
        left_right_continuous_seconds=GAZE_LEFT_RIGHT_CONTINUOUS_SECONDS,
        above_continuous_seconds=GAZE_ABOVE_CONTINUOUS_SECONDS,
        below_continuous_seconds=GAZE_BELOW_CONTINUOUS_SECONDS,
    )

    if glance_completed:
        logged_event = _log_proctoring_event(
            submission,
            ExamProctoringEvent.EVENT_GAZE_VIOLATION,
            severity=ExamProctoringEvent.SEVERITY_WARNING,
            message='Repeated gaze away from the screen',
            source='gaze_ai',
            metadata={**gaze_meta, 'trigger': 'high_confidence_glances', 'detections': glance_threshold},
        )
        _clear_gaze_pending(submission)
        _gaze_mark_violation_logged(submission, now_dt)
    elif should_log and is_no_face:
        logged_event = _log_proctoring_event(
            submission,
            ExamProctoringEvent.EVENT_GAZE_NO_FACE,
            severity=ExamProctoringEvent.SEVERITY_WARNING,
            message='Face not visible to proctoring camera',
            source='gaze_ai',
            metadata=gaze_meta,
        )
    elif should_log and result.is_suspicious:
        logged_event = _log_proctoring_event(
            submission,
            ExamProctoringEvent.EVENT_GAZE_VIOLATION,
            severity=ExamProctoringEvent.SEVERITY_WARNING,
            message=result.label,
            source='gaze_ai',
            metadata=gaze_meta,
        )
        # Start server-side cooldown to prevent the HTTP polling loop from
        # immediately logging a second violation for the same look-away event.
        _gaze_mark_violation_logged(submission, now_dt)

    if logged_event:
        from .gaze_service import reset_submission_state
        reset_submission_state(submission.id)
        # Invalidate the in-memory strike cache so counts are re-read from DB
        _GAZE_STRIKE_CACHE.pop(_gaze_pending_key(submission), None)
        payload['logged_event'] = _serialize_proctoring_event(logged_event)
        evidence = ExamProctoringEvidence.objects.create(
            submission=submission,
            attempt_number=submission.attempt_count,
            event=logged_event,
            evidence_type=ExamProctoringEvidence.TYPE_WEBCAM,
            image=ContentFile(raw, name=f'gaze_{logged_event.id}.jpg'),
            caption='Gaze away from screen' if glance_completed else f'Gaze AI: {result.label}',
        )
        payload['evidence'] = _serialize_proctoring_evidence(evidence, request)

    # force_refresh=True only when a strike was just logged (cache was cleared above)
    strikes = _gaze_strike_counts(submission, force_refresh=logged_event is not None)
    payload.update(strikes)
    payload['limits'] = {
        'gaze_violation': GAZE_VIOLATION_TERMINATE_LIMIT,
        'gaze_no_face': GAZE_NO_FACE_TERMINATE_LIMIT,
    }
    payload['pending_strike'] = (
        gaze_conf_ok and not is_no_face and not should_log and not logged_event
    )
    # Timing info so the frontend can show the direction immediately with a live
    # countdown — no need to wait for a strike to be logged before displaying.
    if gaze_conf_ok and not is_no_face:
        payload['elapsed_seconds'] = round(_gaze_pending_elapsed(submission), 2)
        payload['threshold_seconds'] = float(_gaze_continuous_seconds_for_label(result.label))
    else:
        payload['elapsed_seconds'] = 0.0
        payload['threshold_seconds'] = 0.0
    payload['absent'] = is_no_face
    payload['should_terminate'] = (
        strikes['gaze_violation_count'] >= GAZE_VIOLATION_TERMINATE_LIMIT
        or strikes['gaze_no_face_count'] >= GAZE_NO_FACE_TERMINATE_LIMIT
    )

    return Response(payload, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def student_detect_gadgets(request, exam_id):
    """Detect phones/laptops and warn immediately; terminate after 3 warnings."""
    exam_set = ExamSet.objects.filter(id=exam_id).first()
    if not exam_set:
        return Response({'error': 'Exam not found.'}, status=status.HTTP_404_NOT_FOUND)

    student_email = request.user.email.lower()
    if not _student_can_access_exam(student_email, exam_set):
        return Response({'error': 'You are not enrolled in this exam.'}, status=status.HTTP_403_FORBIDDEN)

    question_id = request.data.get('question_id')
    custom_restrictions_apply = _question_uses_custom_restrictions(exam_set, question_id)
    if custom_restrictions_apply and not exam_set.detect_gadgets:
        return Response({
            'enabled': False,
            'detections': [],
            'detected': False,
            'confirmed': False,
            'warning_count': 0,
            'warning_limit': GADGET_WARNING_TERMINATE_LIMIT,
            'should_terminate': False,
        }, status=status.HTTP_200_OK)

    now_dt = timezone.now()
    submission, created = ExamSubmission.objects.get_or_create(
        exam_set=exam_set,
        student_email=student_email,
        defaults={'started_at': now_dt},
    )
    if submission.is_done:
        return Response({'error': 'No active exam attempt.'}, status=status.HTTP_400_BAD_REQUEST)
    if created:
        from .gaze_service import selected_gaze_model_code
        submission.gaze_model_code = selected_gaze_model_code()
        submission.save(update_fields=['gaze_model_code'])

    image = request.FILES.get('image')
    if not image:
        return Response({'error': 'image file is required.'}, status=status.HTTP_400_BAD_REQUEST)
    raw = image.read()

    try:
        from .gadget_service import (
            gadget_detector_error,
            gadget_detector_ready,
            submit_gadget_detection,
            warm_gadget_detector,
        )
        failure = gadget_detector_error()
        if failure:
            raise RuntimeError(failure)
        if not gadget_detector_ready():
            warm_gadget_detector()
            failure = gadget_detector_error()
            if failure:
                raise RuntimeError(failure)
            return Response({
                'enabled': True,
                'warming': True,
                'detections': [],
                'detected': False,
                'confirmed': False,
                'warning_count': _gadget_warning_count(submission),
                'warning_limit': GADGET_WARNING_TERMINATE_LIMIT,
                'should_terminate': False,
            }, status=status.HTTP_202_ACCEPTED)
        future = submit_gadget_detection(raw)
        if future is None:
            return Response({
                'busy': True,
                'retry_after_ms': 150,
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        detections = future.result(timeout=_GADGET_INFER_TIMEOUT_SECONDS)
    except ValueError:
        return Response({'error': 'Could not decode image.'}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as exc:
        return Response({'error': f'Gadget model unavailable: {exc}'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    key = (submission.id, submission.attempt_count)
    now_ts = _gadget_now_timestamp()
    state = _GADGET_DETECTION_STATE.setdefault(key, {
        'last_logged': 0.0,
        'cleared': True,
        'warning_count': None,
    })
    state.setdefault('cleared', True)
    state.setdefault('last_logged', 0.0)

    logged_event = None
    evidence = None
    confirmed = False
    if detections:
        # Fire on first positive frame of an episode (after a clear stretch).
        # Cooldown blocks flicker double-counts while the phone is still visible.
        can_warn = (
            state.get('cleared', True)
            and now_ts - float(state.get('last_logged') or 0.0) >= _GADGET_WARNING_COOLDOWN_SECONDS
        )
        if can_warn:
            labels = sorted({item['label'] for item in detections})
            logged_event = _log_proctoring_event(
                submission,
                ExamProctoringEvent.EVENT_GADGET_DETECTED,
                severity=ExamProctoringEvent.SEVERITY_WARNING,
                message=f"Prohibited gadget detected: {', '.join(labels)}",
                source='yolo_gadget_ai',
                metadata={
                    'detections': detections,
                    'model': 'yolo11n',
                    'immediate': True,
                },
            )
            evidence = ExamProctoringEvidence.objects.create(
                submission=submission,
                attempt_number=submission.attempt_count,
                event=logged_event,
                evidence_type=ExamProctoringEvidence.TYPE_WEBCAM,
                image=ContentFile(raw, name=f'gadget_{logged_event.id}.jpg'),
                caption=f"Gadget AI: {', '.join(labels)}",
            )
            state['last_logged'] = now_ts
            state['cleared'] = False
            state['warning_count'] = None
            confirmed = True
    else:
        # Device left the frame — next appearance is a fresh warning.
        state['cleared'] = True

    warning_count = _gadget_warning_count(submission, force_refresh=logged_event is not None)
    should_terminate = warning_count >= GADGET_WARNING_TERMINATE_LIMIT

    return Response({
        'enabled': True,
        'detections': detections,
        'detected': bool(detections),
        'confirmed': confirmed,
        'warning_count': warning_count,
        'warning_limit': GADGET_WARNING_TERMINATE_LIMIT,
        'should_terminate': should_terminate,
        'logged_event': _serialize_proctoring_event(logged_event) if logged_event else None,
        'evidence': _serialize_proctoring_evidence(evidence, request) if evidence else None,
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def gaze_model_status(request):
    """Staff: verify gaze AI model is loaded (TrainModel assets)."""
    if not request.user.is_staff:
        return Response({'error': 'Staff access required.'}, status=status.HTTP_403_FORBIDDEN)
    from .gaze_service import gaze_tracker_status
    return Response(gaze_tracker_status(), status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def gaze_model_warmup(request):
    """Begin loading proctoring AI before a student opens an exam."""
    from .gaze_service import warm_gaze_tracker
    from .gadget_service import warm_gadget_detector
    gaze_queued = warm_gaze_tracker()
    gadget_queued = warm_gadget_detector()
    return Response({
        'warming': gaze_queued or gadget_queued,
        'gaze_warming': gaze_queued,
        'gadget_warming': gadget_queued,
    }, status=status.HTTP_202_ACCEPTED)


def _subjective_max_points(question):
    return Decimal(question.points or 1)


def _recalculate_submission_score(submission):
    """Combine auto-graded credit and completed subjective grades."""
    answers = StudentAnswer.objects.filter(
        exam_set=submission.exam_set,
        student_email__iexact=submission.student_email,
    ).select_related('question')
    earned = Decimal('0')
    possible = Decimal('0')
    for answer in answers:
        question = answer.question
        if question.question_type == ExamQuestion.TYPE_ESSAY:
            if answer.awarded_points is None:
                continue
            possible += _subjective_max_points(question)
            earned += answer.awarded_points
            continue

        is_correct, credit = grade_question(question, answer.answer_text)
        if is_correct is None:
            continue
        weight = Decimal(question.points or 1)
        possible += weight
        earned += Decimal(str(credit)) * weight

    score = None
    if possible > 0:
        score = ((earned / possible) * Decimal('100')).quantize(Decimal('0.01'))
    submission.score = score
    submission.save(update_fields=['score'])
    return score


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def instructor_integrity_report(request, subject_id, exam_set_id):
    """Instructor: review a submission's grading and integrity evidence."""
    if not _is_instructor(request.user):
        return Response({'error': 'Instructor access required.'}, status=status.HTTP_403_FORBIDDEN)

    exam_set = ExamSet.objects.filter(
        Q(subject__instructor=request.user) | Q(subject__additional_instructors=request.user),
        id=exam_set_id,
        subject_id=subject_id,
    ).distinct().first()
    if not exam_set:
        return Response({'error': 'Exam set not found.'}, status=status.HTTP_404_NOT_FOUND)

    student_email = (request.query_params.get('student_email') or '').strip().lower()
    if not student_email:
        return Response({'error': 'student_email query parameter is required.'}, status=status.HTTP_400_BAD_REQUEST)

    submission = ExamSubmission.objects.filter(exam_set=exam_set, student_email=student_email).first()
    if not submission:
        return Response({'error': 'No submission found for this student.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'PATCH':
        if not submission.is_done:
            return Response({'error': 'Only submitted exams can be graded.'}, status=status.HTTP_400_BAD_REQUEST)
        grades = request.data.get('grades')
        if not isinstance(grades, list) or not grades:
            return Response({'error': 'A non-empty grades list is required.'}, status=status.HTTP_400_BAD_REQUEST)

        subjective_answers = {
            answer.id: answer
            for answer in StudentAnswer.objects.filter(
                exam_set=exam_set,
                student_email__iexact=student_email,
                question__question_type=ExamQuestion.TYPE_ESSAY,
            ).select_related('question')
        }
        validated = []
        for item in grades:
            try:
                answer_id = int(item.get('answer_id'))
            except (AttributeError, TypeError, ValueError):
                return Response({'error': 'Each grade must include a valid answer_id.'}, status=status.HTTP_400_BAD_REQUEST)
            answer = subjective_answers.get(answer_id)
            if not answer:
                return Response({'error': 'A subjective answer was not found for this submission.'}, status=status.HTTP_404_NOT_FOUND)
            raw_points = item.get('awarded_points')
            if raw_points in (None, ''):
                points = None
            else:
                try:
                    points = Decimal(str(raw_points))
                except (InvalidOperation, TypeError, ValueError):
                    return Response({'error': 'Awarded points must be a number.'}, status=status.HTTP_400_BAD_REQUEST)
                maximum = _subjective_max_points(answer.question)
                if not points.is_finite() or points < 0 or points > maximum:
                    return Response(
                        {'error': f'Awarded points must be between 0 and {maximum}.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                points = points.quantize(Decimal('0.01'))
            validated.append((answer, points))

        with transaction.atomic():
            for answer, points in validated:
                answer.awarded_points = points
                answer.save(update_fields=['awarded_points'])
            _recalculate_submission_score(submission)

    attempt_number = int(request.query_params.get('attempt_number') or submission.attempt_count)
    events = ExamProctoringEvent.objects.filter(
        submission=submission,
        attempt_number=attempt_number,
    ).order_by('created_at')
    evidence = ExamProctoringEvidence.objects.filter(
        submission=submission,
        attempt_number=attempt_number,
    ).order_by('created_at')
    report = ExamIntegrityReport.objects.filter(
        submission=submission,
        attempt_number=attempt_number,
    ).first()

    if submission.is_done:
        report = _build_integrity_report(submission)

    gaze_violation_count = events.filter(
        event_type=ExamProctoringEvent.EVENT_GAZE_VIOLATION,
    ).count()
    gaze_no_face_count = events.filter(
        event_type=ExamProctoringEvent.EVENT_GAZE_NO_FACE,
    ).count()

    subjective_answers = StudentAnswer.objects.filter(
        exam_set=exam_set,
        student_email__iexact=student_email,
        question__question_type=ExamQuestion.TYPE_ESSAY,
    ).select_related('question').order_by('question__order', 'question__created_at')
    subjective_answer_rows = [
        {
            'answer_id': answer.id,
            'question_id': answer.question_id,
            'order': answer.question.order,
            'question_text': answer.question.question_text,
            'answer_text': answer.answer_text,
            'max_points': float(_subjective_max_points(answer.question)),
            'awarded_points': (
                float(answer.awarded_points) if answer.awarded_points is not None else None
            ),
        }
        for answer in subjective_answers
    ]

    return Response(
        {
            'exam_set_id': exam_set.id,
            'exam_title': exam_set.title,
            'student_email': student_email,
            'attempt_number': attempt_number,
            'submission': {
                'is_done': submission.is_done,
                'score': float(submission.score) if submission.score is not None else None,
                'integrity_score': float(submission.integrity_score) if submission.integrity_score is not None else None,
                'terminated': submission.terminated,
                'tab_switches': submission.tab_switches,
                'started_at': submission.started_at,
                'submitted_at': submission.submitted_at,
            },
            'report': {
                'integrity_score': float(report.integrity_score) if report else None,
                'event_count': report.event_count if report else events.count(),
                'warning_count': report.warning_count if report else 0,
                'critical_count': report.critical_count if report else 0,
                'evidence_count': report.evidence_count if report else evidence.count(),
                'tab_switch_count': report.tab_switch_count if report else submission.tab_switches,
                'gaze_violation_count': gaze_violation_count,
                'gaze_no_face_count': gaze_no_face_count,
                'gaze_violation_limit': GAZE_VIOLATION_TERMINATE_LIMIT,
                'gaze_no_face_limit': GAZE_NO_FACE_TERMINATE_LIMIT,
                'summary': report.summary if report else {},
                'narrative': report.narrative if report else '',
                'generated_at': report.generated_at if report else None,
            },
            'events': [_serialize_proctoring_event(e) for e in events],
            'evidence': [_serialize_proctoring_evidence(e, request) for e in evidence],
            'subjective_answers': subjective_answer_rows,
            'manual_grading_complete': bool(subjective_answer_rows) and all(
                answer['awarded_points'] is not None for answer in subjective_answer_rows
            ),
        },
        status=status.HTTP_200_OK,
    )


# ---------------------------------------------------------------------------
# Face Verification Endpoints
# ---------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def student_precheck_face(request, exam_id):
    """Check webcam face size before an exam without starting an attempt."""
    profile = getattr(request.user, 'profile', None)
    if not request.user.is_active or not profile or profile.role != 'student' or not profile.is_enrolled:
        return Response({'error': 'Student access required.'}, status=status.HTTP_403_FORBIDDEN)

    exam_set = ExamSet.objects.select_related('subject').filter(pk=exam_id, is_final=True).first()
    if not exam_set:
        return Response({'error': 'Exam not found.'}, status=status.HTTP_404_NOT_FOUND)
    if not _student_can_access_exam(request.user.email, exam_set):
        return Response({'error': 'You are not enrolled in this exam.'}, status=status.HTTP_403_FORBIDDEN)

    image = request.FILES.get('image')
    if not image:
        return Response({'error': 'Webcam image is required.'}, status=status.HTTP_400_BAD_REQUEST)

    from .face_service import detect_face_position_bytes
    try:
        return Response(detect_face_position_bytes(image.read()))
    except ValueError as exc:
        return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception:
        import logging
        logging.getLogger(__name__).exception('Face precheck failed')
        return Response({'error': 'Face check unavailable. Please retry.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def admin_upload_face_photo(request, student_id):
    """Retire the manual portrait upload path; IDs are student verified."""
    if not request.user.is_superuser:
        return Response({'error': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)
    return Response({'error': 'Students now upload DNSC IDs for automatic verification.'}, status=status.HTTP_410_GONE)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def student_verify_face(request, exam_id):
    """
    POST student/exams/<exam_id>/verify-face/

    Student sends a short webcam sequence at exam start. The backend requires
    a blink before comparing an open-eye frame with the stored face encoding.

    Body (multipart/form-data):
        blink_frames  (Files) — ordered JPEG frames from the student's webcam

    Returns:
        200 OK  — Always returned (check the 'verified' field in the body)
        400     — No image provided, or no face detected in the webcam image
        403     — Student is not enrolled in this exam
        404     — No face photo registered for this student
    """
    user = request.user
    profile = getattr(user, 'profile', None)
    if not user.is_active or not profile or profile.role != 'student' or not profile.is_enrolled:
        return Response({'error': 'Student access required.'}, status=status.HTTP_403_FORBIDDEN)

    # 1. Confirm the exam exists and the student is enrolled
    try:
        exam_set = ExamSet.objects.get(pk=exam_id, is_final=True)
    except ExamSet.DoesNotExist:
        return Response({'error': 'Exam not found.'}, status=status.HTTP_404_NOT_FOUND)

    if not _student_can_access_exam(user.email, exam_set):
        return Response({'error': 'You are not enrolled in this exam.'}, status=status.HTTP_403_FORBIDDEN)

    # 2. Get the student's stored face photo / encoding
    if _effective_face_status(profile) != UserProfile.FACE_STATUS_APPROVED:
        status_msg = 'Upload your DNSC student ID in profile settings for automatic name verification before taking the exam.'
        return Response(
            {'error': status_msg, 'verified': False},
            status=status.HTTP_404_NOT_FOUND,
        )

    if not profile.face_photo:
        return Response(
            {
                'error': 'No face photo is registered for your account. '
                         'Please upload a face photo in your profile settings.',
                'verified': False,
            },
            status=status.HTTP_404_NOT_FOUND,
        )


    # 3. Require an ordered short capture. A single matching photo is never enough.
    uploaded_frames = request.FILES.getlist('blink_frames')
    if not 12 <= len(uploaded_frames) <= 32:
        return Response({'error': 'Capture the blink again to verify your identity.'}, status=status.HTTP_400_BAD_REQUEST)
    if any(frame.size > 250_000 for frame in uploaded_frames):
        return Response({'error': 'Camera frames are too large. Please retry.'}, status=status.HTTP_400_BAD_REQUEST)
    frame_bytes = [frame.read() for frame in uploaded_frames]

    # 4. Check liveness on the server, then match the same capture to the ID.
    from .face_liveness import check_blink_frames
    from .face_service import verify_face_bytes
    try:
        matching_frame = check_blink_frames(frame_bytes)
        if matching_frame is None:
            return Response({
                'verified': False,
                'message': 'Blink not detected. Keep your face in view, close both eyes briefly, then reopen them.',
            }, status=status.HTTP_200_OK)
        result = verify_face_bytes(profile.face_encoding, matching_frame)
        
        if result.get('error'):
            return Response({'error': result['error'], 'verified': False}, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as exc:
        import logging as _logging
        _logging.getLogger(__name__).exception('Blink or face verification failed: %s', exc)
        return Response(
            {'error': 'Face verification is unavailable. Please retry.', 'verified': False},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    # 5. Log the verification attempt as a proctoring event
    try:
        submission = ExamSubmission.objects.filter(
            exam_set=exam_set, student_email=user.email
        ).first()

        if submission:
            event_type = 'face_verified' if result['verified'] else 'face_verification_failed'
            ExamProctoringEvent.objects.create(
                submission=submission,
                attempt_number=submission.attempt_count,
                event_type=ExamProctoringEvent.EVENT_EXAM_STARTED if result['verified'] else ExamProctoringEvent.EVENT_EXAM_TERMINATED,
                severity=ExamProctoringEvent.SEVERITY_INFO if result['verified'] else ExamProctoringEvent.SEVERITY_CRITICAL,
                message=f"Face verification {'passed' if result['verified'] else 'failed'}.",
                source='face_verification',
                metadata={'verified': result['verified']},
            )
    except Exception:
        pass  # Don't let logging failure break the verification response

    # 6. Return result — frontend decides whether to block or proceed
    if result.get('error') and not result['verified']:
        return Response(
            {
                'verified': False,
                'error': result['error'],
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response(
        {
            'verified': result['verified'],
            'message': (
                'Face verified successfully. You may proceed.' if result['verified']
                else 'Face verification failed. Your face does not match the registered photo.'
            ),
        },
        status=status.HTTP_200_OK,
    )
