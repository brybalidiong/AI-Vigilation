import json
import base64
import numpy as np
import cv2
from channels.generic.websocket import AsyncWebsocketConsumer

from accounts.gaze_service import get_gaze_tracker

# ── Confidence gating (must match views.py and inference.py) ─────────────────
# The tracker's raw is_suspicious can fire at lower internal thresholds.
# We re-check confidence here before telling the frontend it's a violation,
# so the UI timer doesn't start on low-confidence frames.
_WS_BELOW_CONFIDENCE   = 0.34
_WS_RIGHT_CONFIDENCE   = 0.30
_WS_LEFT_CONFIDENCE    = 0.28
_WS_ABOVE_CONFIDENCE   = 0.22  # lowered from 0.26 to match inference.py ABOVE_VIOLATION_CONFIDENCE_THRESHOLD
_WS_GENERAL_CONFIDENCE = 0.34


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
        self._frame_count = 0

        # Extract student email from JWT token passed as query param
        query_string = self.scope.get('query_string', b'').decode()
        params = dict(qp.split('=', 1) for qp in query_string.split('&') if '=' in qp)
        token = params.get('token', '')
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
                        self.student_email = user.email
            except Exception:
                pass

        await self.accept()

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return

        try:
            data = json.loads(text_data)
            image_data = data.get('image', '')

            if image_data.startswith('data:image'):
                image_data = image_data.split(',')[1]

            img_bytes = base64.b64decode(image_data)
            nparr = np.frombuffer(img_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if frame is None:
                await self.send(text_data=json.dumps({"error": "Invalid image"}))
                return

            from asgiref.sync import sync_to_async
            tracker = get_gaze_tracker()
            result = await sync_to_async(tracker.analyze)(frame)

            label = result.label or ''
            label_l = label.lower()
            is_no_face = not result.face_detected or label_l in ('no_face', 'multiple_people')

            # Apply confidence gating: don't count as suspicious unless the model
            # is sufficiently confident. This prevents low-confidence below/right
            # frames from starting the violation timer.
            is_suspicious = result.is_suspicious
            if is_suspicious and not is_no_face:
                is_suspicious = _ws_confidence_ok(label, result.confidence)

            payload = {
                "label": label,
                "confidence": result.confidence,
                "face_detected": result.face_detected,
                "is_suspicious": is_suspicious,
                "is_normal": result.is_normal and not is_no_face,
                "face_bbox": result.face_bbox,
            }
            # Send gaze result to student immediately — no waiting
            await self.send(text_data=json.dumps(payload))

            # Save snapshot after response (every 5 frames so instructor live view stays current)
            self._frame_count += 1
            if self.student_email and self._frame_count % 5 == 0:
                import asyncio
                _email = self.student_email
                _exam_id = self.exam_id
                _img_bytes = img_bytes

                async def _bg_save():
                    from asgiref.sync import sync_to_async
                    from accounts.models import ExamSubmission

                    @sync_to_async
                    def do_save():
                        from accounts.gaze_service import save_live_snapshot
                        save_live_snapshot(_exam_id, _email, _img_bytes)

                    await do_save()

                asyncio.ensure_future(_bg_save())

        except Exception as e:
            import traceback
            traceback.print_exc()
            await self.send(text_data=json.dumps({
                "error": str(e),
                "face_detected": True,
                "is_suspicious": False,
                "is_normal": False,
                "label": "error",
            }))
