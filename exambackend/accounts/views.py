from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.db.models import Count
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
from zipfile import BadZipFile

from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

import accounts.firebase_admin  # noqa: F401
from decimal import Decimal, InvalidOperation

from .grading import grade_question
from .models import (
    ExamIntegrityReport,
    ExamProctoringEvent,
    ExamProctoringEvidence,
    ExamQuestion,
    ExamSet,
    ExamSubmission,
    EnrolledStudent,
    StudentAnswer,
    StudentSet,
    Subject,
    UserProfile,
)


def _sync_profile_enrollment_for_email(email: str):
    # Enrollment is now strictly controlled by the admin.
    pass



def _is_instructor(user):
    return bool(user and user.is_authenticated and user.is_staff and not user.is_superuser)


PROCTORING_EVENT_PENALTIES = {
    ExamProctoringEvent.EVENT_TAB_SWITCH: 12,
    ExamProctoringEvent.EVENT_WINDOW_BLUR: 4,
    ExamProctoringEvent.EVENT_SPLIT_SCREEN: 8,
    ExamProctoringEvent.EVENT_COPY_ATTEMPT: 5,
    ExamProctoringEvent.EVENT_CUT_ATTEMPT: 5,
    ExamProctoringEvent.EVENT_SCREENSHOT_ATTEMPT: 10,
    ExamProctoringEvent.EVENT_RIGHT_CLICK: 3,
    ExamProctoringEvent.EVENT_GAZE_VIOLATION: 6,
    ExamProctoringEvent.EVENT_GAZE_NO_FACE: 8,
    ExamProctoringEvent.EVENT_EXAM_TERMINATED: 25,
}

# Auto-terminate exam when gaze strikes reach these limits (each logged strike ≈ 5s apart).
GAZE_VIOLATION_TERMINATE_LIMIT = 8
GAZE_NO_FACE_TERMINATE_LIMIT = 5
GAZE_CONFIDENCE_THRESHOLD = 0.34
GAZE_ABOVE_CONFIDENCE_THRESHOLD = 0.22  # lowered from 0.26 to match inference.py
GAZE_LEFT_CONFIDENCE_THRESHOLD = 0.28
GAZE_RIGHT_CONFIDENCE_THRESHOLD = 0.30
GAZE_BELOW_CONFIDENCE_THRESHOLD = 0.34
GAZE_LEFT_RIGHT_CONTINUOUS_SECONDS = 4.0   # raised: flag at ~4-5s real-world
GAZE_ABOVE_CONTINUOUS_SECONDS = 4.0        # raised: flag at ~4-5s real-world
GAZE_BELOW_CONTINUOUS_SECONDS = 4.0        # raised: flag at ~4-5s real-world
GAZE_CONTINUOUS_SECONDS = 4.0              # raised: flag at ~4-5s real-world
GAZE_NO_FACE_HOLD_SECONDS = 10

# In-memory: (submission_id, attempt) -> {label, at} for continuous gaze strikes.
_GAZE_PENDING_STRIKES: dict[tuple[int, int], dict] = {}
# One no-face strike per absence episode; hold exam after 10s without a face.
_GAZE_NO_FACE_ABSENCE: dict[tuple[int, int], dict] = {}
# Cached strike counts — refreshed from DB only when a new strike is logged.
_GAZE_STRIKE_CACHE: dict[tuple[int, int], dict] = {}
# Tracks when we last saw a suspicious frame — used for grace-period-based clearing.
_GAZE_LAST_SUSPICIOUS: dict[tuple[int, int], object] = {}
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


def _clear_proctoring_for_attempt(submission):
    """Remove logs/evidence/reports when a student starts a fresh attempt."""
    attempt = submission.attempt_count
    ExamProctoringEvent.objects.filter(submission=submission, attempt_number=attempt).delete()
    ExamProctoringEvidence.objects.filter(submission=submission, attempt_number=attempt).delete()
    ExamIntegrityReport.objects.filter(submission=submission, attempt_number=attempt).delete()
    # Clear strike count cache for this attempt
    _GAZE_STRIKE_CACHE.pop((submission.pk, attempt), None)


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
    gaze_violations = counts.get(ExamProctoringEvent.EVENT_GAZE_VIOLATION, 0)
    gaze_no_face = counts.get(ExamProctoringEvent.EVENT_GAZE_NO_FACE, 0)

    narrative_parts = [
        f'Integrity score: {score}%.',
        f'Total logged events: {events.count()}.',
        f'Warnings: {warning_count}, critical: {critical_count}.',
        f'Tab switches: {tab_switch_count}.',
        f'Gaze away from screen: {gaze_violations}.',
        f'Face not visible (gaze): {gaze_no_face}.',
        f'Screenshots/evidence captured: {evidence_qs.count()}.',
    ]
    if submission.terminated:
        narrative_parts.append('Exam was auto-terminated due to proctoring violations.')

    summary = {
        'event_counts': counts,
        'terminated': submission.terminated,
        'tab_switches': submission.tab_switches,
        'gaze_violation_count': gaze_violations,
        'gaze_no_face_count': gaze_no_face,
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

    if username != settings.ADMIN_USERNAME or password != settings.ADMIN_PASSWORD:
        return Response({'error': 'Invalid admin credentials.'}, status=status.HTTP_401_UNAUTHORIZED)

    admin_user, _ = User.objects.get_or_create(
        username=settings.ADMIN_USERNAME,
        defaults={
            'is_staff': True,
            'is_superuser': True,
            'email': '',
        },
    )
    if not admin_user.is_superuser:
        admin_user.is_superuser = True
        admin_user.is_staff = True
        admin_user.save(update_fields=['is_staff', 'is_superuser'])

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


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def admin_instructors(request):
    """Admin: list all registered instructors, or register a new instructor by email."""
    if not _is_admin(request.user):
        return Response({'error': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        instructors = User.objects.filter(is_staff=True, is_superuser=False).select_related('profile')
        data = []
        for u in instructors:
            data.append({
                'id': u.id,
                'username': u.username,
                'email': u.email,
                'first_name': u.first_name,
                'last_name': u.last_name,
                'full_name': u.get_full_name() or u.username,
            })
        return Response({'instructors': data}, status=status.HTTP_200_OK)

    email = (request.data.get('email') or '').strip().lower()
    first_name = (request.data.get('first_name') or '').strip()
    last_name = (request.data.get('last_name') or '').strip()

    if not email:
        return Response({'error': 'Email is required.'}, status=status.HTTP_400_BAD_REQUEST)
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
        # Update to instructor if they exist
        user.is_staff = True
        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name
        user.save()

    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={'role': 'instructor', 'is_enrolled': False},
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
        },
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def admin_instructor_detail(request, instructor_id):
    """Admin: remove an instructor account."""
    if not _is_admin(request.user):
        return Response({'error': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

    instructor = User.objects.filter(id=instructor_id, is_staff=True, is_superuser=False).first()
    if not instructor:
        return Response({'error': 'Instructor not found.'}, status=status.HTTP_404_NOT_FOUND)
    instructor.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


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
                if p.face_photo:
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
                'face_status': p.face_status if p else 'none',
                'face_reupload_allowed': p.face_reupload_allowed if p else False,
                'face_photo_url': face_photo_url,
                'face_pending_photo_url': face_pending_url,
            })
        return Response({'students': data}, status=status.HTTP_200_OK)

    email = (request.data.get('email') or '').strip().lower()
    first_name = (request.data.get('first_name') or '').strip()
    last_name = (request.data.get('last_name') or '').strip()

    if not email:
        return Response({'error': 'Email is required.'}, status=status.HTTP_400_BAD_REQUEST)
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
    if not created:
        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name
        user.save()

    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={'role': 'student', 'is_enrolled': True},
    )
    profile.is_enrolled = True
    if profile.role != 'student':
        profile.role = 'student'
    profile.save(update_fields=['role', 'is_enrolled'])

    return Response(
        {
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'full_name': user.get_full_name() or user.email,
            'is_enrolled': True,
            'created': created,
        },
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def admin_student_detail(request, student_id):
    """Admin: view, update face approval, or remove a student."""
    if not _is_admin(request.user):
        return Response({'error': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

    student = User.objects.filter(id=student_id, is_staff=False).select_related('profile').first()
    if not student or not hasattr(student, 'profile') or student.profile.role != 'student':
        return Response({'error': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)

    profile = student.profile

    if request.method == 'GET':
        face_photo_url = request.build_absolute_uri(profile.face_photo.url) if profile.face_photo else None
        face_pending_url = request.build_absolute_uri(profile.face_pending_photo.url) if profile.face_pending_photo else None
        return Response({
            'id': student.id,
            'email': student.email,
            'full_name': student.get_full_name() or student.email,
            'face_status': profile.face_status,
            'face_reupload_allowed': profile.face_reupload_allowed,
            'face_photo_url': face_photo_url,
            'face_pending_photo_url': face_pending_url,
        })

    if request.method == 'PATCH':
        action = request.data.get('action')

        if action == 'approve_face':
            if not profile.face_pending_photo:
                return Response({'error': 'No pending face photo to approve.'}, status=status.HTTP_400_BAD_REQUEST)

            # If encoding wasn't cached at upload time (older submissions), compute it now.
            if not profile.face_encoding:
                import json as json_module
                from .face_service import extract_face_encoding
                try:
                    encoding = extract_face_encoding(profile.face_pending_photo.path)
                except Exception:
                    encoding = None
                if not encoding:
                    return Response(
                        {'error': 'Could not detect a face in the pending photo. Please reject it and ask the student to re-upload.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                profile.face_encoding = json_module.dumps(encoding)

            # Promote pending photo to the approved slot
            profile.face_photo = profile.face_pending_photo
            profile.face_pending_photo = None
            profile.face_status = UserProfile.FACE_STATUS_APPROVED
            profile.face_reupload_allowed = False
            profile.save(update_fields=['face_photo', 'face_pending_photo', 'face_encoding', 'face_status', 'face_reupload_allowed'])
            return Response({
                'message': 'Face photo approved.',
                'face_status': profile.face_status,
                'face_photo_url': request.build_absolute_uri(profile.face_photo.url) if profile.face_photo else None,
            })


        elif action == 'reject_face':
            if profile.face_pending_photo:
                try:
                    import os
                    os.remove(profile.face_pending_photo.path)
                except Exception:
                    pass
            profile.face_pending_photo = None
            profile.face_encoding = None  # clear cached encoding from upload
            profile.face_status = UserProfile.FACE_STATUS_NONE
            profile.save(update_fields=['face_pending_photo', 'face_encoding', 'face_status'])
            return Response({'message': 'Pending face photo rejected.', 'face_status': profile.face_status})

        elif action == 'toggle_reupload':
            # Flip the reupload flag. If enabling, reset status so student can submit fresh.
            profile.face_reupload_allowed = not profile.face_reupload_allowed
            if profile.face_reupload_allowed:
                profile.face_status = UserProfile.FACE_STATUS_NONE
            profile.save(update_fields=['face_reupload_allowed', 'face_status'])
            return Response({
                'message': 'Re-upload permission updated.',
                'face_reupload_allowed': profile.face_reupload_allowed,
                'face_status': profile.face_status,
            })

        return Response({'error': 'Unknown action. Use approve_face, reject_face, or toggle_reupload.'}, status=status.HTTP_400_BAD_REQUEST)

    # DELETE
    profile.is_enrolled = False
    profile.save(update_fields=['is_enrolled'])
    return Response(status=status.HTTP_204_NO_CONTENT)



@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def enrolled_students(request):
    if not _is_instructor(request.user):
        return Response({'error': 'Instructor access required.'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        qs = EnrolledStudent.objects.filter(student_set__created_by=request.user).select_related(
            'student_set'
        ).order_by('student_set_id', 'email')
        student_set_id = request.query_params.get('student_set_id')
        if student_set_id:
            qs = qs.filter(student_set_id=student_set_id, student_set__created_by=request.user)
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

    roster = StudentSet.objects.filter(id=student_set_id, created_by=request.user).first()
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
        student = EnrolledStudent.objects.create(email=email, student_set=roster)
    except IntegrityError:
        return Response(
            {'error': 'This email is already in this set.'},
            status=status.HTTP_409_CONFLICT,
        )

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

    roster = StudentSet.objects.filter(id=set_id, created_by=request.user).first()
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
        if EnrolledStudent.objects.filter(email__iexact=email, student_set=roster).exists():
            skipped.append(email)
            continue
        try:
            s = EnrolledStudent.objects.create(email=email, student_set=roster)
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
        qs = (
            Subject.objects.filter(instructor=request.user)
            .annotate(student_count=Count('student_sets__students__email', distinct=True))
            .order_by('name')
        )
        rows = [
            {
                'id': s.id,
                'name': s.name,
                'code': s.code,
                'created_at': s.created_at,
                'student_count': s.student_count,
                'announcements': s.announcements,
                'display_photo': s.display_photo.url if s.display_photo else None,
            }
            for s in qs
        ]
        return Response({'subjects': rows}, status=status.HTTP_200_OK)

    name = (request.data.get('name') or '').strip()
    code = (request.data.get('code') or '').strip().upper()
    display_photo = request.FILES.get('display_photo')
    if not name or not code:
        return Response({'error': 'Subject name and code are required.'}, status=status.HTTP_400_BAD_REQUEST)

    if Subject.objects.filter(instructor=request.user, code__iexact=code).exists():
        return Response(
            {'error': 'A subject with this code already exists.'},
            status=status.HTTP_409_CONFLICT,
        )

    subject = Subject.objects.create(instructor=request.user, name=name, code=code, display_photo=display_photo)
    return Response(
        {
            'id': subject.id,
            'name': subject.name,
            'code': subject.code,
            'created_at': subject.created_at,
            'student_count': 0,
            'announcements': subject.announcements,
            'display_photo': subject.display_photo.url if subject.display_photo else None,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(['DELETE', 'PUT'])
@permission_classes([IsAuthenticated])
def instructor_subject_detail(request, subject_id):
    if not _is_instructor(request.user):
        return Response({'error': 'Instructor access required.'}, status=status.HTTP_403_FORBIDDEN)

    subject = Subject.objects.filter(id=subject_id, instructor=request.user).first()
    if not subject:
        return Response({'error': 'Subject not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'PUT':
        announcements = request.data.get('announcements')
        if announcements is not None:
            subject.announcements = announcements
            subject.save()
            return Response({'message': 'Announcements updated'}, status=status.HTTP_200_OK)

    emails = list({e.lower() for e in subject.student_sets.values_list('students__email', flat=True) if e})
    subject.delete()
    for email in emails:
        _sync_profile_enrollment_for_email(email)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def subject_students(request, subject_id):
    if not _is_instructor(request.user):
        return Response({'error': 'Instructor access required.'}, status=status.HTTP_403_FORBIDDEN)

    subject = Subject.objects.filter(id=subject_id, instructor=request.user).first()
    if not subject:
        return Response({'error': 'Subject not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        qs = (
            EnrolledStudent.objects.filter(student_set__subject=subject, student_set__created_by=request.user)
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
        created_by=request.user,
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
        enrollment = EnrolledStudent.objects.create(student_set=roster, email=email)
    except IntegrityError:
        return Response({'error': 'Student already enrolled in this set.'}, status=status.HTTP_409_CONFLICT)

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
            id=enrollment_id,
            student_set__subject_id=subject_id,
            student_set__created_by=request.user,
        )
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
    subject = Subject.objects.filter(id=subject_id, instructor=request.user).first()
    if not subject:
        return Response({'error': 'Subject not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        rows = (
            StudentSet.objects.filter(created_by=request.user, subject=subject)
            .annotate(student_count=Count('students', distinct=True))
            .values('id', 'name', 'created_at', 'student_count')
            .order_by('name')
        )
        return Response({'sets': list(rows)}, status=status.HTTP_200_OK)

    name = (request.data.get('name') or '').strip()
    if not name:
        return Response({'error': 'Set name is required.'}, status=status.HTTP_400_BAD_REQUEST)
    if StudentSet.objects.filter(created_by=request.user, subject=subject, name__iexact=name).exists():
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
            id=set_id,
            subject_id=subject_id,
            created_by=request.user,
        )
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

    subject = Subject.objects.filter(id=subject_id, instructor=request.user).first()
    if not subject:
        return Response({'error': 'Subject not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        rows = []
        for exam in ExamSet.objects.filter(subject=subject).order_by('due_at', '-created_at'):
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
                    'is_final': exam.is_final,
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
    max_attempts_raw = request.data.get('max_attempts', 1)
    time_limit_raw = request.data.get('time_limit', 60)
    assigned_sets_raw = request.data.get('assigned_sets', '[]')
    if not title:
        return Response({'error': 'Exam set title is required.'}, status=status.HTTP_400_BAD_REQUEST)
    if not due_at_raw:
        return Response({'error': 'Due date is required.'}, status=status.HTTP_400_BAD_REQUEST)
    
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
        exam_file=exam_file,
        max_attempts=int(max_attempts_raw) if str(max_attempts_raw).isdigit() else 1,
        time_limit=int(time_limit_raw) if str(time_limit_raw).isdigit() else 60,
    )

    try:
        import json
        assigned_set_ids = json.loads(assigned_sets_raw)
        if isinstance(assigned_set_ids, list) and len(assigned_set_ids) > 0:
            exam_set.assigned_sets.set(assigned_set_ids)
    except:
        pass

    if exam_file:
        try:
            filename = exam_file.name.lower()
            exam_file.seek(0)
            content = exam_file.read().decode('utf-8-sig')
            lines = content.splitlines()

            order = 1
            if filename.endswith('.csv'):
                reader = csv.reader(lines)
                header = next(reader, None)
                for row in reader:
                    if not row or not row[0].strip():
                        continue
                    q_text = row[0].strip()
                    q_type = ExamQuestion.TYPE_MULTIPLE_CHOICE
                    correct_ans = None
                    choices = []

                    if len(row) > 1:
                        cell = row[1].strip().lower()
                        if cell in ('multiple_choice', 'identification'):
                            q_type = cell
                            if len(row) > 2:
                                correct_ans = row[2].strip()
                            choices = [c.strip() for c in row[3:] if c.strip()]
                        else:
                            correct_ans = row[1].strip()
                            choices = [c.strip() for c in row[2:] if c.strip()]

                    ExamQuestion.objects.create(
                        exam_set=exam_set,
                        order=order,
                        question_type=q_type,
                        question_text=q_text,
                        choices=choices if q_type == ExamQuestion.TYPE_MULTIPLE_CHOICE else None,
                        correct_answer=correct_ans
                    )
                    order += 1
            elif filename.endswith('.iken') or filename.endswith('.txt'):
                q_text = ""
                choices = []
                for line in lines:
                    line = line.strip()
                    if not line: continue
                    if line.upper().startswith("ANSWER:"):
                        ans_letter = line[7:].strip().upper()
                        correct_ans_text = None
                        clean_choices = []
                        for c in choices:
                            parts = c.split(maxsplit=1)
                            if not parts: continue
                            prefix = parts[0]
                            text_val = parts[1] if len(parts) > 1 else ""
                            clean_choices.append(text_val)
                            if prefix.rstrip('.)').upper() == ans_letter:
                                correct_ans_text = text_val
                        
                        if q_text and clean_choices and correct_ans_text:
                            ExamQuestion.objects.create(
                                exam_set=exam_set,
                                order=order,
                                question_type=ExamQuestion.TYPE_MULTIPLE_CHOICE,
                                question_text=q_text,
                                choices=clean_choices,
                                correct_answer=correct_ans_text
                            )
                            order += 1
                        q_text = ""
                        choices = []
                    elif not q_text:
                        q_text = line
                    else:
                        choices.append(line)
        except Exception as e:
            pass # fallback to just saving the file if parsing fails
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
            'created_at': exam_set.created_at,
            'exam_file': exam_set.exam_file.url if exam_set.exam_file else None,
            'exam_file_name': exam_set.exam_file.name.split('/')[-1] if exam_set.exam_file else None,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def subject_exam_set_detail(request, subject_id, exam_set_id):
    if not _is_instructor(request.user):
        return Response({'error': 'Instructor access required.'}, status=status.HTTP_403_FORBIDDEN)

    exam_set = ExamSet.objects.filter(
        id=exam_set_id,
        subject_id=subject_id,
        subject__instructor=request.user,
    ).first()
    if not exam_set:
        return Response({'error': 'Exam set not found.'}, status=status.HTTP_404_NOT_FOUND)
    exam_set.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def exam_set_stats(request, subject_id, exam_set_id):
    """Returns the count of students who took the exam per set in the subject."""
    if not _is_instructor(request.user):
        return Response({'error': 'Instructor access required.'}, status=status.HTTP_403_FORBIDDEN)

    exam_set = ExamSet.objects.filter(
        id=exam_set_id,
        subject_id=subject_id,
        subject__instructor=request.user,
    ).first()
    if not exam_set:
        return Response({'error': 'Exam set not found.'}, status=status.HTTP_404_NOT_FOUND)

    students = EnrolledStudent.objects.filter(
        student_set__subject_id=subject_id,
        student_set__created_by=request.user,
    ).select_related('student_set')
    
    submissions = ExamSubmission.objects.filter(exam_set=exam_set).select_related('exam_set')
    submission_map = {sub.student_email.lower(): sub for sub in submissions}

    assigned_ids = set(exam_set.assigned_sets.values_list('id', flat=True)) if exam_set.assigned_sets.exists() else set()

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
            strikes = _gaze_strike_counts(sub, force_refresh=True)
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
        pk=submission_id,
        exam_set_id=exam_set_id,
        exam_set__subject_id=subject_id,
        exam_set__subject__instructor=request.user,
    ).only('latest_snapshot').first()
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

    subject = Subject.objects.filter(id=subject_id, instructor=request.user).first()
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
            student_set__created_by=request.user,
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
        .prefetch_related('assigned_sets', 'questions', 'student_answers')
        .order_by('due_at', '-created_at')
    )
    submissions = ExamSubmission.objects.filter(exam_set__subject=subject)
    submission_map = {
        (row.exam_set_id, row.student_email.lower()): row
        for row in submissions
    }

    rows = []
    for exam in exams:
        assigned_ids = set(exam.assigned_sets.values_list('id', flat=True)) if exam.assigned_sets.exists() else set()
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
            if sub:
                strikes = _gaze_strike_counts(sub, force_refresh=True)
                gaze_v = strikes['gaze_violation_count']
                gaze_nf = strikes['gaze_no_face_count']
            graded_subjective_count = 0
            if sub and subjective_question_ids:
                graded_subjective_count = sum(
                    1
                    for answer in exam.student_answers.all()
                    if answer.student_email.lower() == email
                    and answer.question_id in subjective_question_ids
                    and answer.awarded_points is not None
                )
            pending_subjective_count = max(
                0,
                len(subjective_question_ids) - graded_subjective_count,
            ) if sub and sub.is_done else 0
            rows.append(
                {
                    'exam_set_id': exam.id,
                    'exam_title': exam.title,
                    'available_from': exam.available_from,
                    'due_at': exam.due_at,
                    'student_email': email,
                    'student_set_id': s_id,
                    'student_set_name': set_info.get('set_name'),
                    'is_done': bool(sub and sub.is_done),
                    'score': sub.score if sub and sub.is_done else None,
                    'integrity_score': sub.integrity_score if sub and sub.is_done else None,
                    'submitted_at': sub.submitted_at if sub and sub.is_done else None,
                    'terminated': bool(sub and sub.terminated),
                    'tab_switches': sub.tab_switches if sub else 0,
                    'gaze_violation_count': gaze_v,
                    'gaze_no_face_count': gaze_nf,
                    'subjective_count': len(subjective_question_ids),
                    'pending_subjective_count': pending_subjective_count,
                    'manual_grading_complete': bool(subjective_question_ids) and pending_subjective_count == 0,
                    'has_integrity_report': bool(
                        sub and sub.is_done and (
                            sub.integrity_score is not None
                            or sub.integrity_reports.filter(attempt_number=sub.attempt_count).exists()
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
    subject_exams = (
        ExamSet.objects.filter(subject__student_sets__students__email__iexact=request.user.email)
        .select_related('subject')
        .prefetch_related('assigned_sets__students')
        .distinct()
        .order_by('due_at', '-created_at')
    )
    
    rows = []
    for exam in subject_exams:
        if exam.assigned_sets.exists():
            in_set = exam.assigned_sets.filter(students__email__iexact=request.user.email).exists()
            if not in_set:
                continue
        rows.append(exam)
    
    submissions = ExamSubmission.objects.filter(
        student_email__iexact=request.user.email,
        is_done=True
    ).values('exam_set_id', 'score')
    done_exam_dict = {s['exam_set_id']: s['score'] for s in submissions}

    exams = []
    for exam in rows:
        if not exam.is_final:
            continue
        exams.append(
            {
                'id': exam.id,
                'title': exam.title,
                'description': exam.description,
                'available_from': exam.available_from,
                'due_at': exam.due_at,
                'time_limit': exam.time_limit,
                'is_final': exam.is_final,
                'created_at': exam.created_at,
                'subject_id': exam.subject_id,
                'subject_name': exam.subject.name,
                'subject_code': exam.subject.code,
                'exam_file': exam.exam_file.url if exam.exam_file else None,
                'exam_file_name': exam.exam_file.name.split('/')[-1] if exam.exam_file else None,
                'is_done': exam.id in done_exam_dict,
                'score': done_exam_dict.get(exam.id),
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
                    'face_photo_url': request.build_absolute_uri(profile.face_photo.url) if profile.face_photo else None,
                    'face_pending_photo_url': request.build_absolute_uri(profile.face_pending_photo.url) if profile.face_pending_photo else None,
                    'face_registered': bool(profile.face_encoding),
                    'face_status': profile.face_status,
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

# ---------------------------------------------------------------------------
# PROFILE SETTINGS
# ---------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def update_profile(request):
    """Update the logged-in user's profile settings (including picture upload)."""
    import os as _os
    user = request.user
    profile = getattr(user, 'profile', None)
    if not profile:
        return Response({'error': 'Profile not found.'}, status=status.HTTP_404_NOT_FOUND)

    first_name = request.data.get('first_name', user.first_name)
    last_name = request.data.get('last_name', user.last_name)
    mobile_number = request.data.get('mobile_number', profile.mobile_number)

    user.first_name = first_name
    user.last_name = last_name
    user.save(update_fields=['first_name', 'last_name'])

    profile.mobile_number = mobile_number

    if 'custom_photo' in request.FILES:
        profile.custom_photo = request.FILES['custom_photo']

    face_encoding_error = None
    if 'face_photo' in request.FILES:
        # ── Approval-gate ────────────────────────────────────────────────────
        is_locked = (
            profile.face_status == UserProfile.FACE_STATUS_APPROVED
            and not profile.face_reupload_allowed
        )
        if is_locked:
            face_encoding_error = (
                'Your face photo is already approved and locked. '
                'Contact the admin to allow a new submission.'
            )
        else:
            import json as _json
            face_file = request.FILES['face_photo']
            from .face_service import save_temp_image, extract_face_encoding
            tmp_path = save_temp_image(face_file)
            try:
                # Quick face presence check (reject unusable photos early)
                encoding = extract_face_encoding(tmp_path)
                if not encoding:
                    face_encoding_error = (
                        'Could not detect a face in this photo. '
                        'Please ensure your face is clearly visible and well-lit.'
                    )
                else:
                    face_file.seek(0)
                    # Save to pending slot; store encoding now so approve doesn't need to re-run detection
                    profile.face_pending_photo.save(face_file.name, face_file, save=False)
                    profile.face_encoding = _json.dumps(encoding)  # cached for approval
                    profile.face_status = UserProfile.FACE_STATUS_PENDING
                    profile.face_reupload_allowed = False
            except Exception as exc:
                import logging as _logging
                _logging.getLogger(__name__).error("Face detection raised: %s", exc)
                face_encoding_error = 'Face verification service encountered an error. Please try again.'
            finally:
                _os.unlink(tmp_path)

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
            'face_photo_url': request.build_absolute_uri(profile.face_photo.url) if profile.face_photo else None,
            'face_pending_photo_url': request.build_absolute_uri(profile.face_pending_photo.url) if profile.face_pending_photo else None,
            'face_registered': bool(profile.face_encoding),
            'face_status': profile.face_status,
            'face_reupload_allowed': profile.face_reupload_allowed,
        }
    }
    if face_encoding_error:
        response_data['face_encoding_error'] = face_encoding_error

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
        'case_sensitive': q.case_sensitive,
        'created_at': q.created_at,
    }
    if include_answer:
        data['correct_answer'] = q.correct_answer
    return data


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def exam_questions(request, subject_id, exam_set_id):
    """Instructor: list or create questions for an exam set."""
    if not _is_instructor(request.user):
        return Response({'error': 'Instructor access required.'}, status=status.HTTP_403_FORBIDDEN)

    subject = Subject.objects.filter(id=subject_id, instructor=request.user).first()
    if not subject:
        return Response({'error': 'Subject not found.'}, status=status.HTTP_404_NOT_FOUND)

    exam_set = ExamSet.objects.filter(id=exam_set_id, subject=subject).first()
    if not exam_set:
        return Response({'error': 'Exam set not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        qs = ExamQuestion.objects.filter(exam_set=exam_set)
        return Response(
            {
                'is_final': exam_set.is_final,
                'questions': [_serialize_question(q) for q in qs]
            },
            status=status.HTTP_200_OK,
        )

    if exam_set.is_final:
        return Response({'error': 'Exam is final and cannot be altered.'}, status=status.HTTP_403_FORBIDDEN)

    # POST – create a new question
    question_text = (request.data.get('question_text') or '').strip()
    question_type = (request.data.get('question_type') or '').strip()
    choices_raw = request.data.get('choices')  # list of strings (MC only)
    correct_answer = (request.data.get('correct_answer') or '').strip() or None
    points_raw = request.data.get('points')  # optional hint / item count
    case_sensitive = bool(request.data.get('case_sensitive', False))

    VALID_TYPES = (
        ExamQuestion.TYPE_MULTIPLE_CHOICE,
        ExamQuestion.TYPE_IDENTIFICATION,
        ExamQuestion.TYPE_ENUMERATION,
        ExamQuestion.TYPE_ESSAY,
    )

    if not question_text:
        return Response({'error': 'question_text is required.'}, status=status.HTTP_400_BAD_REQUEST)
    if question_type not in VALID_TYPES:
        return Response(
            {'error': f"question_type must be one of: {', '.join(VALID_TYPES)}."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    choices = None
    points = None

    if question_type == ExamQuestion.TYPE_MULTIPLE_CHOICE:
        if not isinstance(choices_raw, list) or len(choices_raw) < 2:
            return Response(
                {'error': 'Multiple choice questions require at least 2 choices.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        choices = [str(c).strip() for c in choices_raw if str(c).strip()]
        if not correct_answer:
            return Response(
                {'error': 'correct_answer is required for multiple choice questions.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if correct_answer not in choices:
            return Response(
                {'error': 'correct_answer must be one of the provided choices.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        case_sensitive = False  # MC is always case-insensitive (already lowercased on grading)
    elif question_type == ExamQuestion.TYPE_IDENTIFICATION:
        # correct_answer is the expected short answer (optional – instructor may leave blank for fully manual)
        # case_sensitive applies to grading
        pass  # correct_answer and case_sensitive already set above
    elif question_type == ExamQuestion.TYPE_ENUMERATION:
        # correct_answer is a newline-separated list of expected items
        # points is the expected number of items (optional hint)
        try:
            points = int(points_raw) if points_raw is not None else None
        except (ValueError, TypeError):
            points = None
        # case_sensitive applies to per-item matching
    else:
        # essay: no correct answer, no case sensitivity
        correct_answer = None
        case_sensitive = False

    # Auto-assign order = next integer
    last_order = (
        ExamQuestion.objects.filter(exam_set=exam_set).order_by('-order').values_list('order', flat=True).first()
    )
    order = (last_order or 0) + 1

    q = ExamQuestion.objects.create(
        exam_set=exam_set,
        order=order,
        question_type=question_type,
        question_text=question_text,
        choices=choices,
        correct_answer=correct_answer,
        points=points,
        case_sensitive=case_sensitive,
    )
    return Response(_serialize_question(q), status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def exam_question_detail(request, subject_id, exam_set_id, question_id):
    """Instructor: delete a single question."""
    if not _is_instructor(request.user):
        return Response({'error': 'Instructor access required.'}, status=status.HTTP_403_FORBIDDEN)

    subject = Subject.objects.filter(id=subject_id, instructor=request.user).first()
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

    subject = Subject.objects.filter(id=subject_id, instructor=request.user).first()
    if not subject:
        return Response({'error': 'Subject not found.'}, status=status.HTTP_404_NOT_FOUND)

    exam_set = ExamSet.objects.filter(id=exam_set_id, subject=subject).first()
    if not exam_set:
        return Response({'error': 'Exam set not found.'}, status=status.HTTP_404_NOT_FOUND)

    if not exam_set.is_final:
        exam_set.is_final = True
        exam_set.save()
    
    return Response({'message': 'Exam finalized successfully.'}, status=status.HTTP_200_OK)

# ---------------------------------------------------------------------------
# STUDENT – Exam taking endpoints
# ---------------------------------------------------------------------------

def _student_can_access_exam(student_email, exam_set):
    """Return True if the student is enrolled in a set linked to the exam's subject and assigned sets."""
    allowed_qs = EnrolledStudent.objects.filter(
        email__iexact=student_email,
        student_set__subject=exam_set.subject,
    )
    if exam_set.assigned_sets.exists():
        allowed_qs = allowed_qs.filter(student_set__in=exam_set.assigned_sets.all())
    return allowed_qs.exists()


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
    submission, created = ExamSubmission.objects.get_or_create(
        exam_set=exam_set,
        student_email=request.user.email.lower(),
        defaults={'started_at': now}
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
            submission.submitted_at = None
            submission.save()
            _clear_proctoring_for_attempt(submission)
            # Clear gaze smoother state for the new attempt
            from .gaze_service import reset_submission_state
            reset_submission_state(submission.id)
            # Clear previous answers
            StudentAnswer.objects.filter(exam_set=exam_set, student_email=request.user.email.lower()).delete()
        elif not submission.started_at:
            submission.started_at = now
            submission.save(update_fields=['started_at'])

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
    qs = sorted(
        ExamQuestion.objects.filter(exam_set=exam_set),
        key=lambda q: salted_hmac(
            'student-exam-question-order',
            f'{submission.pk}:{submission.attempt_count}:{q.pk}',
            algorithm='sha256',
        ).digest(),
    )
    questions = [
        {**_serialize_question(q, include_answer=False), 'order': position}
        for position, q in enumerate(qs, start=1)
    ]
    return Response({
        'questions': questions,
        'started_at': submission.started_at,
        'time_limit': exam_set.time_limit
    }, status=status.HTTP_200_OK)


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
    gaze_violations = int(request.data.get('gaze_violations', 0))
    gaze_no_face = int(request.data.get('gaze_no_face', 0))
    termination_reason = (request.data.get('termination_reason') or '').strip()

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
    elif terminated:
        end_message = f'Exam auto-terminated (tab switches: {tab_switches}).'

    _log_proctoring_event(
        submission,
        end_event,
        severity=ExamProctoringEvent.SEVERITY_CRITICAL if terminated else ExamProctoringEvent.SEVERITY_INFO,
        message=end_message,
        source='submit',
        metadata={
            'tab_switches': tab_switches,
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
        submission.save(update_fields=['started_at'])

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
        submission.save(update_fields=['started_at'])

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
        submission.save(update_fields=['started_at'])

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
    forced_label = _resolve_forced_gaze_label(
        request.data.get('forced_label', '').strip(),
        [result.label],
    )
    logged_event = None
    is_no_face = not result.face_detected or result.label in ('no_face', 'multiple_people')
    gaze_conf_ok = result.is_suspicious and _gaze_violation_confidence_ok(
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
    if record_strike and forced_label and gaze_conf_ok and not is_no_face:
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

    if should_log and is_no_face:
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
            caption=f'Gaze AI: {result.label}',
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def gaze_model_status(request):
    """Staff: verify gaze AI model is loaded (TrainModel assets)."""
    if not request.user.is_staff:
        return Response({'error': 'Staff access required.'}, status=status.HTTP_403_FORBIDDEN)
    from .gaze_service import gaze_tracker_status
    return Response(gaze_tracker_status(), status=status.HTTP_200_OK)


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
        id=exam_set_id,
        subject_id=subject_id,
        subject__instructor=request.user,
    ).first()
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
def admin_upload_face_photo(request, student_id):
    """
    POST admin/students/<student_id>/face-photo/

    Admin uploads a formal face photo for a student.
    The backend extracts and stores the face encoding in UserProfile.face_encoding.

    Body (multipart/form-data):
        face_photo  (File) — The formal face photo (JPG/PNG recommended)

    Returns:
        200 OK    — Encoding extracted and saved successfully
        400       — No face detected in the uploaded photo
        403       — Caller is not a superuser/admin
        404       — Student not found
    """
    if not request.user.is_superuser:
        return Response({'error': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

    try:
        profile = UserProfile.objects.select_related('user').get(pk=student_id, role='student')
    except UserProfile.DoesNotExist:
        return Response({'error': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)

    uploaded_file = request.FILES.get('face_photo')
    if not uploaded_file:
        return Response({'error': 'No face_photo file provided.'}, status=status.HTTP_400_BAD_REQUEST)

    import os
    from .face_service import save_temp_image, extract_face_encoding
    tmp_path = save_temp_image(uploaded_file)
    try:
        encoding = extract_face_encoding(tmp_path)
    finally:
        os.unlink(tmp_path)  # Always clean up temp file

    if encoding is None:
        return Response(
            {'error': 'No face detected in the uploaded photo. Please use a clear, front-facing photo.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    import json as json_module
    # Save the photo file and the encoding
    profile.face_photo.save(uploaded_file.name, uploaded_file, save=False)
    profile.face_encoding = json_module.dumps(encoding)
    profile.save(update_fields=['face_photo', 'face_encoding'])

    return Response(
        {
            'message': 'Face photo uploaded and encoding saved successfully.',
            'student_email': profile.user.email,
            'face_photo_url': request.build_absolute_uri(profile.face_photo.url) if profile.face_photo else None,
        },
        status=status.HTTP_200_OK,
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def student_verify_face(request, exam_id):
    """
    POST student/exams/<exam_id>/verify-face/

    Student sends a webcam snapshot at exam start. The backend compares it
    against the stored face encoding and returns whether they match.

    Body (multipart/form-data):
        webcam_image  (File) — JPEG/PNG snapshot from the student's webcam

    Returns:
        200 OK  — Always returned (check the 'verified' field in the body)
        400     — No image provided, or no face detected in the webcam image
        403     — Student is not enrolled in this exam
        404     — No face photo registered for this student
    """
    user = request.user

    # 1. Confirm the exam exists and the student is enrolled
    try:
        exam_set = ExamSet.objects.get(pk=exam_id)
    except ExamSet.DoesNotExist:
        return Response({'error': 'Exam not found.'}, status=status.HTTP_404_NOT_FOUND)

    is_enrolled = EnrolledStudent.objects.filter(
        email__iexact=user.email,
        student_set__subject=exam_set.subject
    ).exists()
    if not is_enrolled:
        return Response({'error': 'You are not enrolled in this exam.'}, status=status.HTTP_403_FORBIDDEN)

    # 2. Get the student's stored face photo / encoding
    try:
        profile = UserProfile.objects.get(user=user)
    except UserProfile.DoesNotExist:
        return Response({'error': 'Student profile not found.'}, status=status.HTTP_404_NOT_FOUND)

    if profile.face_status != UserProfile.FACE_STATUS_APPROVED:
        status_msg = {
            UserProfile.FACE_STATUS_NONE: (
                'No face photo has been submitted for your account. '
                'Please upload a face photo in your profile settings and wait for admin approval.'
            ),
            UserProfile.FACE_STATUS_PENDING: (
                'Your face photo is pending admin approval. '
                'Please wait for the administrator to review your submission before taking the exam.'
            ),
        }.get(profile.face_status, 'Your face photo has not been approved by the admin.')
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


    # 3. Get the uploaded webcam image
    webcam_file = request.FILES.get('webcam_image')
    if not webcam_file:
        return Response({'error': 'No webcam_image file provided.'}, status=status.HTTP_400_BAD_REQUEST)

    # 4. Run face verification
    from .face_service import verify_face_bytes
    try:
        result = verify_face_bytes(profile.face_encoding, webcam_file.read())
        
        if result.get('error'):
            return Response({'error': result['error'], 'verified': False}, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as exc:
        import logging as _logging
        _logging.getLogger(__name__).error("verify_face raised: %s", exc)
        return Response(
            {'error': 'Verification service error.', 'verified': False}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
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
