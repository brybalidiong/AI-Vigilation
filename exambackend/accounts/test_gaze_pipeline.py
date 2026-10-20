import asyncio
import base64
import json
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import numpy as np
from django.core import signing
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient

from accounts import gaze_service
from accounts.models import (
    EnrolledStudent, ExamProctoringEvent, ExamProctoringEvidence, ExamQuestion, ExamSet, ExamSubmission,
    StudentSet, Subject,
)
from gaze_tracker.tracker import GazeResult, GazeTracker


def suspicious_result():
    return GazeResult('Looking at the left', 0.82, True, False, True)


class GazeWarmupTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='warmup-student',
            email='warmup@example.com',
        )
        self.client = APIClient()

    def test_authenticated_student_can_queue_non_blocking_warmup(self):
        self.client.force_authenticate(self.user)
        with patch('accounts.gaze_service.warm_gaze_tracker', return_value=True) as warm, \
                patch('accounts.gadget_service.warm_gadget_detector', return_value=True) as gadget_warm:
            response = self.client.post('/api/gaze/warmup/')
        self.assertEqual(response.status_code, 202)
        self.assertTrue(response.data['warming'])
        warm.assert_called_once_with()
        gadget_warm.assert_called_once_with()

    def test_warmup_requires_authentication(self):
        response = self.client.post('/api/gaze/warmup/')
        self.assertEqual(response.status_code, 401)


class GadgetWarmupStateTests(SimpleTestCase):
    def test_failed_background_warmup_is_not_ready(self):
        from concurrent.futures import Future
        from accounts import gadget_service

        failed = Future()
        failed.set_exception(RuntimeError('synthetic model failure'))
        with patch.object(gadget_service, '_warmup_future', failed), patch.object(
            gadget_service.get_gadget_detector, 'cache_info',
            return_value=type('CacheInfo', (), {'currsize': 1})(),
        ):
            self.assertFalse(gadget_service.gadget_detector_ready())
            self.assertEqual(str(gadget_service.gadget_detector_error()), 'synthetic model failure')
            self.assertFalse(gadget_service.warm_gadget_detector())

    def test_busy_detector_drops_new_frame_instead_of_queueing_it(self):
        from accounts import gadget_service

        first, second = Future(), Future()
        with patch.object(gadget_service, '_infer_slots', threading.BoundedSemaphore(1)), \
                patch.object(gadget_service, 'GADGET_EXECUTOR') as executor:
            executor.submit.side_effect = [first, second]
            self.assertIs(gadget_service.submit_gadget_detection(b'first'), first)
            self.assertIsNone(gadget_service.submit_gadget_detection(b'stale'))
            first.set_result([])
            self.assertIs(gadget_service.submit_gadget_detection(b'fresh'), second)
            second.set_result([])
            self.assertEqual(executor.submit.call_count, 2)


class GazeFrameTests(SimpleTestCase):
    def test_busy_gaze_worker_does_not_queue_stale_frames(self):
        first, second = Future(), Future()
        with patch.object(gaze_service, '_inference_slots', threading.BoundedSemaphore(1)), \
                patch.object(gaze_service, 'GAZE_EXECUTOR') as executor:
            executor.submit.side_effect = [first, second]
            self.assertIs(gaze_service.submit_gaze_inference(lambda raw: raw, b'first'), first)
            self.assertIsNone(gaze_service.submit_gaze_inference(lambda raw: raw, b'stale'))
            first.set_result(None)
            self.assertIs(gaze_service.submit_gaze_inference(lambda raw: raw, b'fresh'), second)
            second.set_result(None)
            self.assertEqual(executor.submit.call_count, 2)

    async def test_busy_gaze_worker_returns_matching_frame_id_without_inference(self):
        from accounts.consumers import GazeConsumer

        consumer = GazeConsumer()
        consumer.exam_id = 1
        consumer.student_email = None
        consumer.send = AsyncMock()
        with patch('accounts.consumers.submit_gaze_inference', return_value=None), \
                patch('accounts.consumers.analyze_frame_bytes') as analyze:
            await consumer.receive(text_data=json.dumps({
                'image': base64.b64encode(b'jpeg').decode(), 'frame_id': 23,
            }))
        self.assertEqual(json.loads(consumer.send.call_args.kwargs['text_data']), {
            'busy': True, 'frame_id': 23,
        })
        analyze.assert_not_called()

    def test_gaze_socket_uses_local_channel_layer(self):
        from channels.layers import InMemoryChannelLayer, get_channel_layer
        from accounts.consumers import GazeConsumer

        self.assertEqual(GazeConsumer.channel_layer_alias, 'gaze')
        self.assertIsInstance(get_channel_layer('gaze'), InMemoryChannelLayer)

    async def test_websocket_rejects_missing_token_before_inference_setup(self):
        from accounts.consumers import GazeConsumer

        consumer = GazeConsumer()
        consumer.scope = {'url_route': {'kwargs': {'exam_id': 1}}, 'query_string': b''}
        consumer.close = AsyncMock()
        consumer.accept = AsyncMock()
        await consumer.connect()
        consumer.close.assert_awaited_once_with(code=4401)
        consumer.accept.assert_not_awaited()

    async def test_websocket_rejects_student_without_exam_access(self):
        from accounts.consumers import GazeConsumer
        from rest_framework_simplejwt.tokens import AccessToken

        token = AccessToken()
        token['user_id'] = 123
        consumer = GazeConsumer()
        consumer.scope = {
            'url_route': {'kwargs': {'exam_id': 1}},
            'query_string': f'token={token}'.encode(),
        }
        consumer.close = AsyncMock()
        consumer.accept = AsyncMock()
        with patch.object(GazeConsumer, '_authorized_student_email', new_callable=AsyncMock, return_value=None):
            await consumer.connect()
        consumer.close.assert_awaited_once_with(code=4403)
        consumer.accept.assert_not_awaited()

    def test_receipt_binds_result_to_image_student_exam_and_expiry(self):
        raw = b'exact analyzed jpeg'
        with patch('django.core.signing.time.time', return_value=1000):
            receipt = gaze_service.sign_gaze_result(1, 'student@example.com', raw, suspicious_result())
        with patch('django.core.signing.time.time', return_value=1001):
            result = gaze_service.read_gaze_result(receipt, 1, 'student@example.com', raw)
            self.assertEqual(result.label, 'Looking at the left')
            self.assertEqual(result.confidence, 0.82)
            for exam, email, image in [
                (2, 'student@example.com', raw),
                (1, 'someone@example.com', raw),
                (1, 'student@example.com', b'later webcam frame'),
            ]:
                with self.assertRaises(signing.BadSignature):
                    gaze_service.read_gaze_result(receipt, exam, email, image)
        with patch('django.core.signing.time.time', return_value=1016):
            with self.assertRaises(signing.SignatureExpired):
                gaze_service.read_gaze_result(receipt, 1, 'student@example.com', raw)

    async def test_slow_snapshot_storage_does_not_block_next_ws_detection(self):
        from accounts.consumers import GazeConsumer
        release = threading.Event()
        upload_started = threading.Event()

        def slow_save(*args):
            upload_started.set()
            release.wait(5)

        consumer = GazeConsumer()
        consumer.exam_id = 1
        consumer.student_email = 'student@example.com'
        consumer._last_snapshot_at = 0
        consumer.send = AsyncMock()
        executor = ThreadPoolExecutor(max_workers=1)
        try:
            with patch.object(gaze_service, '_snapshot_executor', executor), \
                    patch.object(gaze_service, 'close_old_connections'), \
                    patch.object(gaze_service, 'save_live_snapshot', side_effect=slow_save), \
                    patch('accounts.consumers.analyze_frame_bytes', return_value=suspicious_result()):
                message = {'image': base64.b64encode(b'jpeg').decode(), 'frame_id': 1}
                await consumer.receive(text_data=json.dumps(message))
                await asyncio.to_thread(upload_started.wait, 2)
                self.assertTrue(upload_started.is_set())
                message['frame_id'] = 2
                await asyncio.wait_for(consumer.receive(text_data=json.dumps(message)), timeout=1)
                payload = json.loads(consumer.send.call_args.kwargs['text_data'])
                self.assertEqual(payload['frame_id'], 2)
                self.assertIn('frame_receipt', payload)
                self.assertFalse(release.is_set())
                release.set()
                await asyncio.to_thread(executor.shutdown, wait=True)
        finally:
            release.set()
            executor.shutdown(wait=True)

    async def test_websocket_treats_disabled_below_direction_as_normal(self):
        from accounts.consumers import GazeConsumer

        consumer = GazeConsumer()
        consumer.exam_id = 1
        consumer.student_email = None
        consumer._last_snapshot_at = 0
        consumer._closed = False
        consumer._horizontal_candidate = ''
        consumer._horizontal_streak = 0
        consumer._restrictions = {
            'gaze_above': True,
            'gaze_below': False,
            'gaze_left': True,
            'gaze_right': True,
        }
        consumer._essay_question_ids = {7}
        consumer.send = AsyncMock()
        below_result = GazeResult('Looking below', 0.82, True, False, True)

        with patch('accounts.consumers.analyze_frame_bytes', return_value=below_result):
            await consumer.receive(text_data=json.dumps({
                'image': base64.b64encode(b'jpeg').decode(),
                'frame_id': 1,
                'question_id': 7,
            }))

        payload = json.loads(consumer.send.call_args.kwargs['text_data'])
        self.assertFalse(payload['direction_enabled'])
        self.assertFalse(payload['is_suspicious'])
        self.assertTrue(payload['is_normal'])

    async def test_websocket_confirms_horizontal_direction_twice(self):
        from accounts.consumers import GazeConsumer

        consumer = GazeConsumer()
        consumer.exam_id = 1
        consumer.student_email = None
        consumer._last_snapshot_at = 0
        consumer.send = AsyncMock()
        message = {'image': base64.b64encode(b'jpeg').decode(), 'frame_id': 1}
        with patch('accounts.consumers.analyze_frame_bytes', return_value=suspicious_result()):
            await consumer.receive(text_data=json.dumps(message))
            first = json.loads(consumer.send.call_args.kwargs['text_data'])
            self.assertFalse(first['is_suspicious'])
            self.assertTrue(first['stabilizing'])

            message['frame_id'] = 2
            await consumer.receive(text_data=json.dumps(message))
            second = json.loads(consumer.send.call_args.kwargs['text_data'])
            self.assertTrue(second['is_suspicious'])
            self.assertFalse(second['stabilizing'])

    def test_live_snapshot_backlog_is_bounded(self):
        with patch.object(gaze_service, '_snapshot_slots', threading.BoundedSemaphore(1)), \
                patch.object(gaze_service._snapshot_executor, 'submit') as submit:
            self.assertTrue(gaze_service.schedule_live_snapshot(1, 's@example.com', b'jpeg'))
            self.assertFalse(gaze_service.schedule_live_snapshot(1, 's@example.com', b'jpeg'))
            submit.assert_called_once()

    def test_missing_model_returns_unavailable_instead_of_lock_error(self):
        tracker = GazeTracker(assets_dir='missing-gaze-test-assets')
        self.assertEqual(tracker.analyze(np.zeros((4, 4, 3), dtype=np.uint8)).label,
                         'gaze_model_unavailable')

    def test_browser_pixels_are_not_flipped_before_detection(self):
        from types import SimpleNamespace
        tracker = GazeTracker(assets_dir='missing-gaze-test-assets')
        tracker._ready = True
        seen = []
        tracker._landmarker = SimpleNamespace(detect=lambda image: (
            seen.append(image.numpy_view().copy()) or SimpleNamespace(face_landmarks=[])
        ))
        frame = np.zeros((4, 6, 3), dtype=np.uint8)
        frame[:, 0] = [0, 0, 255]
        tracker.analyze(frame)
        self.assertTrue(np.all(seen[0][:, 0] == [255, 0, 0]))
        self.assertTrue(np.all(seen[0][:, -1] == 0))

    def test_strong_sideways_geometry_uses_student_perspective(self):
        from gaze_tracker.inference import _pick_sideways_from_geometry
        for sign, expected in [(-1, 1), (1, 2)]:
            geo = np.zeros(14, dtype=np.float32)
            geo[5] = geo[7] = sign * 0.2
            result = _pick_sideways_from_geometry(geo, 1, 2, 0.1, 0.1, 0.1)
            self.assertEqual(result[0], expected)

    def test_camera_geometry_keeps_head_yaw_and_corrects_eye_direction(self):
        from gaze_tracker.inference import mirror_correct_geo, pick_gaze_label

        classes = [
            'Looking above the screen', 'Looking at the left',
            'Looking at the right', 'Looking at the screen (Normal)',
            'Looking below',
        ]
        for yaw, expected in [(0.2, 1), (-0.2, 2)]:
            geo = np.zeros(14, dtype=np.float32)
            geo[0] = geo[11] = yaw
            corrected = mirror_correct_geo(geo)
            self.assertAlmostEqual(float(corrected[0]), yaw)
            self.assertAlmostEqual(float(corrected[11]), yaw)
            opposite = 2 if expected == 1 else 1
            probabilities = np.array([0.02, 0.02, 0.02, 0.14, 0.02], dtype=np.float32)
            probabilities[opposite] = 0.80
            direction, _ = pick_gaze_label(probabilities, corrected, classes)
            self.assertEqual(direction, expected)

        geo = np.zeros(14, dtype=np.float32)
        geo[5] = geo[7] = 0.2
        corrected = mirror_correct_geo(geo)
        self.assertLess(corrected[5], 0)
        self.assertLess(corrected[7], 0)

    def test_clear_eye_direction_wins_over_opposite_head_turn(self):
        from gaze_tracker.inference import pick_gaze_label

        classes = [
            'Looking above the screen', 'Looking at the left',
            'Looking at the right', 'Looking at the screen (Normal)',
            'Looking below',
        ]
        geo = np.zeros(14, dtype=np.float32)
        geo[0] = -0.20  # head turns right
        geo[5] = geo[7] = -0.20  # eyes clearly look left
        probs = np.array([0.02, 0.05, 0.80, 0.10, 0.03], dtype=np.float32)
        direction, _ = pick_gaze_label(probs, geo, classes)
        self.assertEqual(direction, 1)

    def test_small_deliberate_vertical_gaze_reaches_geometry_threshold(self):
        from gaze_tracker.inference import is_looking_above, is_looking_below

        above = np.zeros(14, dtype=np.float32)
        above[6] = above[8] = -0.019
        above[12] = -0.041
        self.assertTrue(is_looking_above(above))

        below = np.zeros(14, dtype=np.float32)
        below[6] = below[8] = 0.115
        below[12] = 0.155
        self.assertTrue(is_looking_below(below))

    def test_model_supported_vertical_geometry_displaces_normal_in_one_frame(self):
        from gaze_tracker.inference import pick_gaze_label

        classes = [
            'Looking above the screen', 'Looking at the left',
            'Looking at the right', 'Looking at the screen (Normal)',
            'Looking below',
        ]
        for iris_v, vert, iris_h, probabilities, expected in (
            (-0.07, -0.045, 0.00, [0.23, 0.02, 0.02, 0.68, 0.05], 0),
            (-0.019, -0.041, 0.00, [0.24, 0.02, 0.02, 0.67, 0.05], 3),
            (0.115, 0.155, 0.00, [0.02, 0.02, 0.02, 0.67, 0.27], 4),
            (0.090, 0.125, 0.00, [0.02, 0.02, 0.02, 0.68, 0.26], 4),
            (0.20, 0.16, 0.00, [0.02, 0.02, 0.02, 0.68, 0.26], 4),
            (-0.07, -0.045, -0.20, [0.23, 0.02, 0.02, 0.68, 0.05], 0),
        ):
            with self.subTest(iris_v=iris_v):
                geo = np.zeros(14, dtype=np.float32)
                geo[6] = geo[8] = iris_v
                geo[5] = geo[7] = iris_h
                geo[12] = vert
                direction, confidence = pick_gaze_label(np.array(probabilities, dtype=np.float32), geo, classes)
                self.assertEqual(direction, expected)
                self.assertGreaterEqual(confidence, 0.22 if expected == 0 else 0.25)

    def test_normal_eye_jitter_does_not_become_above(self):
        from gaze_tracker.inference import pick_gaze_label

        classes = [
            'Looking above the screen', 'Looking at the left',
            'Looking at the right', 'Looking at the screen (Normal)',
            'Looking below',
        ]
        geo = np.zeros(14, dtype=np.float32)
        geo[1] = -0.05
        geo[6] = geo[8] = -0.025
        geo[12] = -0.045
        for probabilities in (
            [0.23, 0.02, 0.02, 0.69, 0.04],
            [0.40, 0.02, 0.02, 0.38, 0.18],
        ):
            direction, _ = pick_gaze_label(np.array(probabilities, dtype=np.float32), geo, classes)
            self.assertEqual(direction, 3)

        geo[6] = geo[8] = -0.07
        direction, _ = pick_gaze_label(
            np.array([0.23, 0.02, 0.02, 0.69, 0.04], dtype=np.float32), geo, classes,
        )
        self.assertEqual(direction, 0)

        geo[1] = 0
        geo[6] = -0.12
        geo[8] = 0
        direction, _ = pick_gaze_label(
            np.array([0.23, 0.02, 0.02, 0.69, 0.04], dtype=np.float32), geo, classes,
        )
        self.assertEqual(direction, 3)

    def test_borderline_above_requires_clearer_evidence(self):
        from gaze_tracker.inference import pick_gaze_label

        classes = [
            'Looking above the screen', 'Looking at the left',
            'Looking at the right', 'Looking at the screen (Normal)',
            'Looking below',
        ]
        geo = np.zeros(14, dtype=np.float32)
        geo[6] = geo[8] = -0.055
        geo[12] = -0.045
        direction, _ = pick_gaze_label(
            np.array([0.23, 0.02, 0.02, 0.68, 0.05], dtype=np.float32), geo, classes,
        )
        self.assertEqual(direction, 3)

        geo[6] = geo[8] = 0
        for above_confidence, expected in ((0.60, 3), (0.80, 3)):
            with self.subTest(above_confidence=above_confidence):
                direction, _ = pick_gaze_label(
                    np.array([above_confidence, 0.02, 0.02, 0.10, 0.06], dtype=np.float32),
                    geo, classes,
                )
                self.assertEqual(direction, expected)

    def test_sideways_look_does_not_become_weak_below(self):
        from gaze_tracker.inference import pick_gaze_label

        classes = [
            'Looking above the screen', 'Looking at the left',
            'Looking at the right', 'Looking at the screen (Normal)',
            'Looking below',
        ]
        for iris_h, expected in ((-0.20, 1), (0.20, 2)):
            with self.subTest(iris_h=iris_h):
                geo = np.zeros(14, dtype=np.float32)
                geo[5] = geo[7] = iris_h
                geo[6] = geo[8] = 0.11
                geo[12] = 0.15
                probs = np.array([0.02, 0.04, 0.04, 0.62, 0.28], dtype=np.float32)
                direction, confidence = pick_gaze_label(probs, geo, classes)
                self.assertEqual(direction, expected)
                self.assertGreaterEqual(confidence, 0.50)

                # The same false direction may be the model's weak argmax.
                weak_below = np.array([0.03, 0.22, 0.04, 0.32, 0.39], dtype=np.float32)
                direction, _ = pick_gaze_label(weak_below, geo, classes)
                self.assertEqual(direction, expected)

                # A clearly downward iris position remains a below reading.
                geo[6] = geo[8] = 0.21
                direction, _ = pick_gaze_label(probs, geo, classes)
                self.assertEqual(direction, 4)

    def test_obvious_opposite_vertical_iris_blocks_model_label(self):
        from gaze_tracker.inference import pick_gaze_label

        classes = [
            'Looking above the screen', 'Looking at the left',
            'Looking at the right', 'Looking at the screen (Normal)',
            'Looking below',
        ]
        for iris_v, vert, probabilities in (
            (0.16, 0.17, [0.80, 0.02, 0.02, 0.12, 0.04]),
            (-0.08, -0.06, [0.04, 0.02, 0.02, 0.12, 0.80]),
        ):
            with self.subTest(iris_v=iris_v):
                geo = np.zeros(14, dtype=np.float32)
                geo[6] = geo[8] = iris_v
                geo[12] = vert
                direction, _ = pick_gaze_label(np.array(probabilities, dtype=np.float32), geo, classes)
                self.assertEqual(direction, 3)

    def test_vertical_override_requires_matching_iris_movement(self):
        from gaze_tracker.inference import pick_gaze_label

        classes = [
            'Looking above the screen', 'Looking at the left',
            'Looking at the right', 'Looking at the screen (Normal)',
            'Looking below',
        ]
        for pitch, vert, iris_v, probabilities in (
            (-0.20, -0.20, 0.0, [0.23, 0.02, 0.02, 0.71, 0.02]),
            (-0.50, -0.20, 0.16, [0.25, 0.02, 0.02, 0.65, 0.06]),
            (0.20, 0.20, 0.0, [0.02, 0.02, 0.02, 0.68, 0.26]),
        ):
            with self.subTest(pitch=pitch, iris_v=iris_v):
                geo = np.zeros(14, dtype=np.float32)
                geo[1] = pitch
                geo[12] = vert
                geo[6] = geo[8] = iris_v
                direction, _ = pick_gaze_label(np.array(probabilities, dtype=np.float32), geo, classes)
                self.assertEqual(direction, 3)

    def test_tracker_keeps_vertical_labels_at_direction_confidence_gate(self):
        classes = [
            'Looking above the screen', 'Looking at the left',
            'Looking at the right', 'Looking at the screen (Normal)',
            'Looking below',
        ]
        tracker = GazeTracker(assets_dir='missing-gaze-test-assets')
        tracker._ready = True
        tracker.classes = classes
        tracker._landmarker = SimpleNamespace(detect=lambda image: SimpleNamespace(face_landmarks=[[None]]))
        tracker._interpreter = Mock()
        tracker._interpreter.get_tensor.return_value = np.array([[0.23, 0.02, 0.02, 0.47, 0.26]], dtype=np.float32)
        tracker._img_idx = tracker._out_idx = 0
        tracker._has_geo_input = False
        tracker._smoother = None
        tracker._hysteresis = None
        frame = np.zeros((8, 8, 3), dtype=np.uint8)

        with patch.object(tracker, '_crop_face', return_value=(frame, None)), \
                patch('gaze_tracker.tracker.extract_geometric_features', return_value=np.zeros(14, dtype=np.float32)), \
                patch('gaze_tracker.tracker.pick_gaze_label', side_effect=[(0, 0.23), (4, 0.26)]):
            for expected in (classes[0], classes[4]):
                result = tracker.analyze(frame)
                self.assertEqual(result.label, expected)
                self.assertFalse(result.is_normal)
                self.assertTrue(result.is_suspicious)

    def test_strong_geometry_corrects_opposite_horizontal_model_class(self):
        from gaze_tracker.inference import pick_gaze_label

        # The CNN can still carry the opposite horizontal label after a
        # mirrored capture. An unambiguous iris displacement must win so the
        # student-facing direction is stable.
        geo = np.zeros(14, dtype=np.float32)
        geo[5] = geo[7] = -0.20
        probs = np.array([0.02, 0.05, 0.80, 0.10, 0.03], dtype=np.float32)
        idx, confidence = pick_gaze_label(probs, geo, [
            'Looking above the screen', 'Looking at the left',
            'Looking at the right', 'Looking at the screen (Normal)',
            'Looking below',
        ])
        self.assertEqual(idx, 1)
        self.assertGreaterEqual(confidence, 0.50)

    def test_sideways_geometry_beats_above_without_upward_evidence(self):
        from gaze_tracker.inference import pick_gaze_label

        geo = np.zeros(14, dtype=np.float32)
        geo[5] = geo[7] = -0.20
        classes = [
            'Looking above the screen', 'Looking at the left',
            'Looking at the right', 'Looking at the screen (Normal)',
            'Looking below',
        ]
        for expected, probs in (
            (1, [0.80, 0.05, 0.02, 0.10, 0.03]),
            (4, [0.02, 0.05, 0.03, 0.10, 0.80]),
        ):
            idx, confidence = pick_gaze_label(np.array(probs, dtype=np.float32), geo, classes)
            self.assertEqual(idx, expected)
            self.assertGreaterEqual(confidence, 0.50)

        geo[6] = geo[8] = -0.08
        idx, confidence = pick_gaze_label(
            np.array([0.80, 0.05, 0.02, 0.10, 0.03], dtype=np.float32), geo, classes,
        )
        self.assertEqual(idx, 0)
        self.assertAlmostEqual(confidence, 0.80)

        geo[6] = geo[8] = 0
        geo[5] = geo[7] = 0
        geo[1] = -0.20
        idx, _ = pick_gaze_label(
            np.array([0.80, 0.05, 0.02, 0.10, 0.03], dtype=np.float32), geo, classes,
        )
        self.assertEqual(idx, 0)

    def test_rightward_eyes_beat_false_above_prediction(self):
        from gaze_tracker.inference import pick_gaze_label

        classes = [
            'Looking above the screen', 'Looking at the left',
            'Looking at the right', 'Looking at the screen (Normal)',
            'Looking below',
        ]
        geo = np.zeros(14, dtype=np.float32)
        geo[5] = geo[7] = 0.18
        for probabilities in (
            [0.80, 0.02, 0.05, 0.10, 0.03],
            [0.23, 0.02, 0.05, 0.67, 0.03],
        ):
            with self.subTest(probabilities=probabilities):
                idx, confidence = pick_gaze_label(
                    np.array(probabilities, dtype=np.float32), geo, classes,
                )
                self.assertEqual(idx, 2)
                self.assertGreaterEqual(confidence, 0.50)

    def test_face_verification_skips_mirrored_pass_after_original_matches(self):
        from accounts import face_service

        recognizer = patch.object(face_service, '_get_recognizer').start()
        recognizer.return_value.match.return_value = 0.5
        self.addCleanup(patch.stopall)
        image = np.zeros((120, 160, 3), dtype=np.uint8)
        features = np.zeros((1, 128), dtype=np.float32)
        with patch.object(face_service, '_load_image_bytes', return_value=image), \
                patch.object(face_service, '_get_face_features', return_value=features) as extract:
            result = face_service.verify_face_bytes(json.dumps([0.0] * 128), b'jpeg')
        self.assertTrue(result['verified'])
        extract.assert_called_once()


@override_settings(STORAGES={'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'}})
class GazeEvidenceTests(TestCase):
    def setUp(self):
        instructor = User.objects.create(username='teacher')
        self.student = User.objects.create(username='student', email='student@example.com')
        subject = Subject.objects.create(name='Science', code='SCI', instructor=instructor)
        roster = StudentSet.objects.create(name='A', subject=subject)
        EnrolledStudent.objects.create(email=self.student.email, student_set=roster)
        self.exam = ExamSet.objects.create(subject=subject, title='Exam', is_final=True)
        self.client = APIClient()
        self.client.force_authenticate(self.student)
        self.raw = b'exact frame from websocket'
        self.receipt = gaze_service.sign_gaze_result(
            self.exam.pk, self.student.email, self.raw, suspicious_result(),
        )
        from accounts import views
        for cache in (views._GAZE_STRIKE_CACHE, views._GAZE_LAST_LOGGED,
                      views._GAZE_PENDING_STRIKES, views._GAZE_NO_FACE_ABSENCE,
                      views._GADGET_DETECTION_STATE):
            cache.clear()

    def post_frame(self, **fields):
        return self.client.post(f'/api/student/exams/{self.exam.pk}/proctoring/gaze/', {
            'image': SimpleUploadedFile('gaze.jpg', self.raw, content_type='image/jpeg'),
            'frame_receipt': self.receipt, **fields,
        })

    def test_evidence_uses_classified_frame_without_inference_or_preview_upload(self):
        with patch.object(gaze_service, 'analyze_frame_bytes') as analyze, \
                patch.object(gaze_service, 'schedule_live_snapshot') as snapshot:
            response = self.post_frame(record_strike='true', forced_label='Looking at the left')
        self.assertEqual(response.status_code, 200, response.data)
        analyze.assert_not_called()
        snapshot.assert_not_called()
        evidence = ExamProctoringEvidence.objects.get()
        self.assertEqual(evidence.image.read(), self.raw)
        self.assertEqual(evidence.event.metadata['confidence'], 0.82)
        self.assertEqual(response.data['gaze_violation_count'], 1)

    def test_observation_does_not_duplicate_ws_violation_timing(self):
        with patch('accounts.views._gaze_continuous_strike_ready') as timer:
            response = self.post_frame(observe_only='true')
        self.assertEqual(response.status_code, 200)
        timer.assert_not_called()
        self.assertFalse(ExamProctoringEvidence.objects.exists())

    def test_disabled_below_direction_cannot_record_a_strike(self):
        self.exam.detect_gaze_below = False
        self.exam.save(update_fields=['detect_gaze_below'])
        below_result = GazeResult('Looking below', 0.82, True, False, True)
        self.receipt = gaze_service.sign_gaze_result(
            self.exam.pk, self.student.email, self.raw, below_result,
        )

        essay = ExamQuestion.objects.create(
            exam_set=self.exam,
            question_type=ExamQuestion.TYPE_ESSAY,
            question_text='Explain.',
        )
        response = self.post_frame(
            record_strike='true',
            forced_label='Looking below',
            question_id=essay.pk,
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(response.data['direction_enabled'])
        self.assertFalse(response.data['is_suspicious'])
        self.assertTrue(response.data['is_normal'])
        self.assertNotIn('logged_event', response.data)
        self.assertFalse(ExamProctoringEvidence.objects.exists())

    def test_disabled_essay_direction_remains_enabled_for_objective_question(self):
        self.exam.detect_gaze_below = False
        self.exam.save(update_fields=['detect_gaze_below'])
        objective = ExamQuestion.objects.create(
            exam_set=self.exam,
            question_type=ExamQuestion.TYPE_MULTIPLE_CHOICE,
            question_text='Choose.',
            choices=['A', 'B'],
            correct_answer='A',
        )
        below_result = GazeResult('Looking below', 0.82, True, False, True)
        self.receipt = gaze_service.sign_gaze_result(
            self.exam.pk, self.student.email, self.raw, below_result,
        )

        response = self.post_frame(
            record_strike='true',
            forced_label='Looking below',
            question_id=objective.pk,
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data['direction_enabled'])
        self.assertIsNotNone(response.data.get('logged_event'))

    def test_tampered_frame_is_rejected_without_inference(self):
        self.raw = b'different image'
        with patch.object(gaze_service, 'analyze_frame_bytes') as analyze:
            response = self.post_frame(record_strike='true', forced_label='Looking at the left')
        self.assertEqual(response.status_code, 400)
        analyze.assert_not_called()
        self.assertFalse(ExamProctoringEvidence.objects.exists())

    def test_gadget_warns_immediately_then_terminates_after_three(self):
        detection = [{'label': 'cell phone', 'confidence': 0.91, 'box': [1, 2, 30, 40]}]
        url = f'/api/student/exams/{self.exam.pk}/proctoring/gadgets/'
        started = timezone.now()
        # Clear frames between detections so each appearance is a new warning.
        check_times = [
            (started + timedelta(seconds=offset)).timestamp()
            for offset in (0, 1, 4, 5, 8, 9, 12)
        ]
        detect_side_effect = [
            detection,  # warn 1
            [],         # clear
            detection,  # warn 2
            [],         # clear
            detection,  # warn 3 → terminate
            detection,  # still detected after terminate threshold
            [],
        ]

        with patch('accounts.gadget_service.gadget_detector_ready', return_value=True), \
                patch('accounts.gadget_service.detect_gadgets', side_effect=detect_side_effect), \
                patch('accounts.views._gadget_now_timestamp', side_effect=check_times):
            responses = [
                self.client.post(url, {
                    'image': SimpleUploadedFile(
                        f'gadget-{index}.jpg', self.raw, content_type='image/jpeg',
                    ),
                })
                for index in range(5)
            ]

        self.assertEqual([response.status_code for response in responses], [200] * 5)
        self.assertTrue(responses[0].data['confirmed'])
        self.assertEqual(responses[0].data['warning_count'], 1)
        self.assertFalse(responses[0].data['should_terminate'])
        self.assertFalse(responses[1].data['confirmed'])
        self.assertTrue(responses[2].data['confirmed'])
        self.assertEqual(responses[2].data['warning_count'], 2)
        self.assertTrue(responses[4].data['confirmed'])
        self.assertEqual(responses[4].data['warning_count'], 3)
        self.assertTrue(responses[4].data['should_terminate'])
        self.assertEqual(
            ExamProctoringEvent.objects.filter(event_type='gadget_detected').count(),
            3,
        )

    def test_gadget_continuous_hold_counts_as_one_warning(self):
        detection = [{'label': 'cell phone', 'confidence': 0.91, 'box': [1, 2, 30, 40]}]
        url = f'/api/student/exams/{self.exam.pk}/proctoring/gadgets/'
        started = timezone.now()
        check_times = [
            (started + timedelta(seconds=offset)).timestamp()
            for offset in range(4)
        ]

        with patch('accounts.gadget_service.gadget_detector_ready', return_value=True), patch(
            'accounts.gadget_service.detect_gadgets',
            return_value=detection,
        ), patch('accounts.views._gadget_now_timestamp', side_effect=check_times):
            responses = [
                self.client.post(url, {
                    'image': SimpleUploadedFile(
                        f'gadget-hold-{index}.jpg', self.raw, content_type='image/jpeg',
                    ),
                })
                for index in range(4)
            ]

        confirmed = [response.data['confirmed'] for response in responses]
        self.assertEqual(confirmed.count(True), 1)
        self.assertEqual(responses[-1].data['warning_count'], 1)
        self.assertFalse(responses[-1].data['should_terminate'])
        self.assertEqual(ExamProctoringEvent.objects.filter(event_type='gadget_detected').count(), 1)

    def test_disabled_gadget_restriction_skips_inference(self):
        self.exam.detect_gadgets = False
        self.exam.save(update_fields=['detect_gadgets'])
        essay = ExamQuestion.objects.create(
            exam_set=self.exam,
            question_type=ExamQuestion.TYPE_ESSAY,
            question_text='Explain.',
        )
        url = f'/api/student/exams/{self.exam.pk}/proctoring/gadgets/'

        with patch('accounts.gadget_service.detect_gadgets') as detect:
            response = self.client.post(url, {
                'image': SimpleUploadedFile('gadget.jpg', self.raw, content_type='image/jpeg'),
                'question_id': essay.pk,
            })

        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(response.data['enabled'])
        detect.assert_not_called()

    def test_disabled_essay_gadget_detection_remains_enabled_for_objective_question(self):
        self.exam.detect_gadgets = False
        self.exam.save(update_fields=['detect_gadgets'])
        objective = ExamQuestion.objects.create(
            exam_set=self.exam,
            question_type=ExamQuestion.TYPE_MULTIPLE_CHOICE,
            question_text='Choose.',
            choices=['A', 'B'],
            correct_answer='A',
        )
        detection = [{'label': 'cell phone', 'confidence': 0.91, 'box': [1, 2, 30, 40]}]
        url = f'/api/student/exams/{self.exam.pk}/proctoring/gadgets/'

        with patch('accounts.gadget_service.gadget_detector_ready', return_value=True), \
                patch('accounts.gadget_service.detect_gadgets', return_value=detection):
            response = self.client.post(url, {
                'image': SimpleUploadedFile('gadget.jpg', self.raw, content_type='image/jpeg'),
                'question_id': objective.pk,
            })

        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data['enabled'])
        self.assertTrue(response.data['detected'])

    def test_cold_gadget_model_reports_warming_instead_of_unavailable(self):
        url = f'/api/student/exams/{self.exam.pk}/proctoring/gadgets/'

        with patch('accounts.gadget_service.gadget_detector_ready', return_value=False), \
                patch('accounts.gadget_service.warm_gadget_detector', return_value=True) as warm, \
                patch('accounts.gadget_service.detect_gadgets') as detect:
            response = self.client.post(url, {
                'image': SimpleUploadedFile('gadget.jpg', self.raw, content_type='image/jpeg'),
            })

        self.assertEqual(response.status_code, 202, response.data)
        self.assertTrue(response.data['warming'])
        warm.assert_called_once_with()
        detect.assert_not_called()

    def test_busy_gadget_model_requests_a_fresh_frame(self):
        url = f'/api/student/exams/{self.exam.pk}/proctoring/gadgets/'
        with patch('accounts.gadget_service.gadget_detector_ready', return_value=True), \
                patch('accounts.gadget_service.submit_gadget_detection', return_value=None):
            response = self.client.post(url, {
                'image': SimpleUploadedFile('gadget.jpg', self.raw, content_type='image/jpeg'),
            })

        self.assertEqual(response.status_code, 429, response.data)
        self.assertTrue(response.data['busy'])
        self.assertEqual(response.data['retry_after_ms'], 150)
        self.assertFalse(ExamProctoringEvent.objects.exists())

    def test_failed_gadget_warmup_returns_unavailable(self):
        url = f'/api/student/exams/{self.exam.pk}/proctoring/gadgets/'
        with patch('accounts.gadget_service.gadget_detector_error', return_value=RuntimeError('synthetic failure')), \
                patch('accounts.gadget_service.detect_gadgets') as detect:
            response = self.client.post(url, {
                'image': SimpleUploadedFile('gadget.jpg', self.raw, content_type='image/jpeg'),
            })
        self.assertEqual(response.status_code, 503, response.data)
        self.assertIn('synthetic failure', response.data['error'])
        detect.assert_not_called()


@override_settings(STORAGES={'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'}})
class InstructorLiveSnapshotTests(TestCase):
    def setUp(self):
        self.instructor = User.objects.create(username='teacher-snapshot', is_staff=True)
        subject = Subject.objects.create(name='Science', code='SNAP', instructor=self.instructor)
        roster = StudentSet.objects.create(name='A', subject=subject, created_by=self.instructor)
        EnrolledStudent.objects.create(email='student@example.com', student_set=roster)
        self.exam = ExamSet.objects.create(subject=subject, title='Exam', is_final=True)
        self.submission = ExamSubmission.objects.create(
            exam_set=self.exam, student_email='student@example.com', started_at=None,
        )
        self.image_bytes = b'jpeg snapshot bytes'
        self.submission.latest_snapshot.save(
            'snapshot.jpg',
            SimpleUploadedFile('snapshot.jpg', self.image_bytes, content_type='image/jpeg'),
        )
        self.client = APIClient()
        self.client.force_authenticate(self.instructor)

    def test_stats_snapshot_is_served_by_authenticated_api(self):
        stats = self.client.get(
            f'/api/instructor/subjects/{self.exam.subject_id}/exam-sets/{self.exam.pk}/stats/'
        )
        self.assertEqual(stats.status_code, 200, stats.data)
        snapshot_url = stats.data['examinees'][0]['snapshot_url']
        self.assertIn(f'/submissions/{self.submission.pk}/snapshot/', snapshot_url)

        snapshot = self.client.get(snapshot_url)
        self.assertEqual(snapshot.status_code, 200)
        self.assertEqual(snapshot['Content-Type'], 'image/jpeg')
        self.assertEqual(b''.join(snapshot.streaming_content), self.image_bytes)

    def test_new_live_snapshot_removes_replaced_storage_object(self):
        previous_name = self.submission.latest_snapshot.name
        storage = self.submission.latest_snapshot.storage

        gaze_service.save_live_snapshot(self.exam.pk, 'student@example.com', b'next synthetic jpeg')

        self.submission.refresh_from_db()
        self.assertNotEqual(self.submission.latest_snapshot.name, previous_name)
        self.assertFalse(storage.exists(previous_name))
        self.assertTrue(storage.exists(self.submission.latest_snapshot.name))

    def test_other_instructor_cannot_read_snapshot(self):
        other = User.objects.create(username='other-teacher', is_staff=True)
        self.client.force_authenticate(other)
        response = self.client.get(
            f'/api/instructor/subjects/{self.exam.subject_id}/exam-sets/{self.exam.pk}'
            f'/submissions/{self.submission.pk}/snapshot/'
        )
        self.assertEqual(response.status_code, 404)
