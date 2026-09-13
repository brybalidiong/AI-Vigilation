import json
import base64
import asyncio
import time
from dataclasses import replace
from urllib.parse import parse_qs
from channels.generic.websocket import AsyncWebsocketConsumer

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


class GazeConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.exam_id = self.scope['url_route']['kwargs']['exam_id']
        self.student_email = None
        self._last_snapshot_at = 0
        self._closed = False
        self._horizontal_candidate = ''
        self._horizontal_streak = 0

        # Extract student email from JWT token passed as query param
        query_string = self.scope.get('query_string', b'').decode()
        token = parse_qs(query_string).get('token', [''])[0]
        if token:
            try:
                from rest_framework_simplejwt.tokens import AccessToken
                access = AccessToken(token)
                user_id = access.get('user_id')
                if user_id:
                    from asgiref.sync import sync_to_async
                    from django.contrib.auth import get_user_model
                    User = get_user_model()
                    user = await sync_to_async(User.objects.filter(id=user_id).first)()
                    if user:
                        self.student_email = (user.email or '').lower()
            except Exception:
                pass

        await self.accept()

    async def disconnect(self, close_code):
        self._closed = True

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return

        try:
            data = json.loads(text_data)
            image_data = data.get('image', '')

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
            is_suspicious = result.is_suspicious
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
            signed_result = replace(
                result,
                is_suspicious=is_suspicious,
                is_normal=bool(result.is_normal and not is_no_face),
            )
            payload = {
                "label": label,
                "confidence": result.confidence,
                "face_detected": result.face_detected,
                "is_no_face": is_no_face,
                "is_suspicious": is_suspicious,
                "is_normal": result.is_normal and not is_no_face,
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
