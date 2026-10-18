import json
import base64
import asyncio
import time
from dataclasses import replace
from urllib.parse import parse_qs
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

from accounts.exam_updates import subject_exam_group

from accounts.gaze_service import (
    GAZE_EXECUTOR, analyze_frame_bytes, schedule_live_snapshot, sign_gaze_result,
)

# ── Confidence gating (must match views.py and inference.py) ─────────────────
# The tracker's raw is_suspicious can fire at lower internal thresholds.
# We re-check confidence here before telling the frontend it's a violation,
# so the UI timer doesn't start on low-confidence frames.
_WS_BELOW_CONFIDENCE   = 0.34
_WS_RIGHT_CONFIDENCE   = 0.30
_WS_LEFT_CONFIDENCE    = 0.28
_WS_ABOVE_CONFIDENCE   = 0.22  # lowered from 0.26 to match inference.py ABOVE_VIOLATION_CONFIDENCE_THRESHOLD
_WS_GENERAL_CONFIDENCE = 0.34
_HORIZONTAL_CONFIRM_FRAMES = 2


def _horizontal_direction(label: str) -> str:
    value = (label or '').lower()
    if 'left' in value and 'right' not in value:
        return 'left'
    if 'right' in value and 'left' not in value:
        return 'right'
    return ''


def _ws_confidence_ok(label: str, confidence: float) -> bool:
    """Apply the same per-direction confidence gate as views.py."""
    l = (label or '').lower()
    if 'below' in l:
        return confidence >= _WS_BELOW_CONFIDENCE
    if 'right' in l and 'left' not in l:
        return confidence >= _WS_RIGHT_CONFIDENCE
    if 'left' in l and 'right' not in l:
        return confidence >= _WS_LEFT_CONFIDENCE
    if 'above' in l:
        return confidence >= _WS_ABOVE_CONFIDENCE
    return confidence >= _WS_GENERAL_CONFIDENCE


def _ws_direction_enabled(label: str, restrictions: dict) -> bool:
    value = (label or '').lower()
    if 'above' in value:
        return restrictions.get('gaze_above', True)
    if 'below' in value:
        return restrictions.get('gaze_below', True)
    if 'left' in value and 'right' not in value:
        return restrictions.get('gaze_left', True)
    if 'right' in value and 'left' not in value:
        return restrictions.get('gaze_right', True)
    return True


class StudentExamUpdatesConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        query_string = self.scope.get('query_string', b'').decode()
        token = parse_qs(query_string).get('token', [''])[0]
        self.groups_joined = []

        try:
            from rest_framework_simplejwt.tokens import AccessToken

            user_id = AccessToken(token).get('user_id')
            subject_ids = await self._student_subject_ids(user_id)
        except Exception:
            await self.close(code=4401)
            return

        if subject_ids is None:
            await self.close(code=4403)
            return

        for subject_id in subject_ids:
            group = subject_exam_group(subject_id)
            await self.channel_layer.group_add(group, self.channel_name)
            self.groups_joined.append(group)
        await self.accept()

    @database_sync_to_async
    def _student_subject_ids(self, user_id):
        from django.contrib.auth import get_user_model
        from accounts.models import EnrolledStudent

        user = get_user_model().objects.filter(
            pk=user_id, is_active=True, profile__role='student', profile__is_enrolled=True,
        ).first()
        if user is None:
            return None
        return list(
            EnrolledStudent.objects.filter(
                email__iexact=user.email, student_set__subject__isnull=False,
            ).values_list('student_set__subject_id', flat=True).distinct()
        )

    async def disconnect(self, close_code):
        for group in getattr(self, 'groups_joined', []):
            await self.channel_layer.group_discard(group, self.channel_name)

    async def exam_published(self, event):
        await self.send(text_data=json.dumps({'type': 'exam_published'}))


class GazeConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.exam_id = self.scope['url_route']['kwargs']['exam_id']
        self.student_email = None
        self._last_snapshot_at = 0
        self._closed = False
        self._horizontal_candidate = ''
        self._horizontal_streak = 0
        self._restrictions = {
            'gaze_above': True,
            'gaze_below': True,
            'gaze_left': True,
            'gaze_right': True,
        }
        self._essay_question_ids = set()

        query_string = self.scope.get('query_string', b'').decode()
        token = parse_qs(query_string).get('token', [''])[0]
        try:
            from rest_framework_simplejwt.tokens import AccessToken
            user_id = AccessToken(token).get('user_id')
        except Exception:
            await self.close(code=4401)
            return

        self.student_email = await self._authorized_student_email(user_id)
        if not self.student_email:
            await self.close(code=4403)
            return

        from asgiref.sync import sync_to_async
        from accounts.models import ExamQuestion, ExamSet
        restriction_values = await sync_to_async(
            lambda: ExamSet.objects.filter(pk=self.exam_id).values(
                'detect_gaze_above',
                'detect_gaze_below',
                'detect_gaze_left',
                'detect_gaze_right',
            ).first(),
            thread_sensitive=True,
        )()
        if restriction_values:
            self._restrictions = {
                'gaze_above': restriction_values['detect_gaze_above'],
                'gaze_below': restriction_values['detect_gaze_below'],
                'gaze_left': restriction_values['detect_gaze_left'],
                'gaze_right': restriction_values['detect_gaze_right'],
            }
        self._essay_question_ids = set(await sync_to_async(
            lambda: list(ExamQuestion.objects.filter(
                exam_set_id=self.exam_id,
                question_type=ExamQuestion.TYPE_ESSAY,
            ).values_list('id', flat=True)),
            thread_sensitive=True,
        )())

        await self.accept()

    @database_sync_to_async
    def _authorized_student_email(self, user_id):
        from django.contrib.auth import get_user_model
        from accounts.models import ExamSet
        from accounts.views import _student_can_access_exam

        user = get_user_model().objects.filter(
            pk=user_id, is_active=True, profile__role='student', profile__is_enrolled=True,
        ).first()
        exam = ExamSet.objects.select_related('subject').filter(
            pk=self.exam_id, is_final=True,
        ).first()
        if not user or not exam or not _student_can_access_exam(user.email, exam):
            return None
        return (user.email or '').lower()

    async def disconnect(self, close_code):
        self._closed = True

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return

        try:
            data = json.loads(text_data)
            image_data = data.get('image', '')
            try:
                question_id = int(data.get('question_id'))
            except (TypeError, ValueError):
                question_id = None

            if image_data.startswith('data:image'):
                image_data = image_data.split(',')[1]

            img_bytes = base64.b64decode(image_data, validate=True)
            started = time.perf_counter()
            result = await asyncio.get_running_loop().run_in_executor(
                GAZE_EXECUTOR, analyze_frame_bytes, img_bytes,
            )
            if getattr(self, '_closed', False):
                return

            label = result.label or ''
            label_l = label.lower()
            is_no_face = not result.face_detected or label_l in ('no_face', 'multiple_people')

            # Apply confidence gating: don't count as suspicious unless the model
            # is sufficiently confident. This prevents low-confidence below/right
            # frames from starting the violation timer.
            direction_enabled = (
                _ws_direction_enabled(label, getattr(self, '_restrictions', {}))
                if question_id in getattr(self, '_essay_question_ids', set())
                else True
            )
            is_suspicious = result.is_suspicious and direction_enabled
            if is_suspicious and not is_no_face:
                is_suspicious = _ws_confidence_ok(label, result.confidence)

            # A single horizontal prediction is often ordinary eye jitter.
            # Confirm the same side twice (normally well under half a second)
            # before starting the browser's violation timer.
            horizontal = _horizontal_direction(label)
            stabilizing = False
            if is_suspicious and horizontal:
                if getattr(self, '_horizontal_candidate', '') == horizontal:
                    self._horizontal_streak = getattr(self, '_horizontal_streak', 0) + 1
                else:
                    self._horizontal_candidate = horizontal
                    self._horizontal_streak = 1
                stabilizing = self._horizontal_streak < _HORIZONTAL_CONFIRM_FRAMES
                if stabilizing:
                    is_suspicious = False
            else:
                self._horizontal_candidate = ''
                self._horizontal_streak = 0

            # Sign the effective result after the same confidence gate returned
            # to the browser. Evidence replay therefore uses exactly the state
            # that drove the live timer.
            effective_normal = bool(
                (result.is_normal or (result.is_suspicious and not direction_enabled))
                and not is_no_face
            )
            signed_result = replace(
                result,
                is_suspicious=is_suspicious,
                is_normal=effective_normal,
            )
            payload = {
                "label": label,
                "confidence": result.confidence,
                "face_detected": result.face_detected,
                "is_no_face": is_no_face,
                "is_suspicious": is_suspicious,
                "is_normal": effective_normal,
                "direction_enabled": direction_enabled,
                "stabilizing": stabilizing,
                "face_bbox": result.face_bbox,
                "frame_id": data.get('frame_id'),
                "processing_ms": round((time.perf_counter() - started) * 1000, 1),
            }
            if self.student_email:
                payload['frame_receipt'] = sign_gaze_result(
                    self.exam_id, self.student_email, img_bytes, signed_result,
                )
            # Send gaze result to student immediately — no waiting
            await self.send(text_data=json.dumps(payload))

            # Slow remote storage cannot block inference or build a backlog.
            if self.student_email and time.monotonic() - self._last_snapshot_at >= 3:
                self._last_snapshot_at = time.monotonic()
                schedule_live_snapshot(self.exam_id, self.student_email, img_bytes)

        except Exception as e:
            import traceback
            traceback.print_exc()
            if getattr(self, '_closed', False):
                return
            await self.send(text_data=json.dumps({
                "error": str(e),
                "face_detected": True,
                "is_suspicious": False,
                "is_normal": False,
                "label": "error",
            }))
