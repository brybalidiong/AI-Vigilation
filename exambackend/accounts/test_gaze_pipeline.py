import asyncio
import base64
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest.mock import AsyncMock, patch

import numpy as np
from django.core import signing
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient

from accounts import gaze_service
from accounts.models import (
    EnrolledStudent, ExamProctoringEvidence, ExamSet, ExamSubmission,
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


class GazeFrameTests(SimpleTestCase):
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
        consumer.send = AsyncMock()
        below_result = GazeResult('Looking below', 0.82, True, False, True)

        with patch('accounts.consumers.analyze_frame_bytes', return_value=below_result):
            await consumer.receive(text_data=json.dumps({
                'image': base64.b64encode(b'jpeg').decode(),
                'frame_id': 1,
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

        response = self.post_frame(record_strike='true', forced_label='Looking below')

        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(response.data['direction_enabled'])
        self.assertFalse(response.data['is_suspicious'])
        self.assertTrue(response.data['is_normal'])
        self.assertNotIn('logged_event', response.data)
        self.assertFalse(ExamProctoringEvidence.objects.exists())

    def test_tampered_frame_is_rejected_without_inference(self):
        self.raw = b'different image'
        with patch.object(gaze_service, 'analyze_frame_bytes') as analyze:
            response = self.post_frame(record_strike='true', forced_label='Looking at the left')
        self.assertEqual(response.status_code, 400)
        analyze.assert_not_called()
        self.assertFalse(ExamProctoringEvidence.objects.exists())

    def test_gadget_requires_three_continuous_seconds_then_logs_evidence(self):
        detection = [{'label': 'cell phone', 'confidence': 0.91, 'box': [1, 2, 30, 40]}]
        url = f'/api/student/exams/{self.exam.pk}/proctoring/gadgets/'
        started = timezone.now()
        check_times = [
            (started + timedelta(seconds=offset)).timestamp()
            for offset in range(4)
        ]

        with patch('accounts.gadget_service.detect_gadgets', return_value=detection), \
                patch('accounts.views._gadget_now_timestamp', side_effect=check_times):
            responses = [
                self.client.post(url, {
                    'image': SimpleUploadedFile(
                        f'gadget-{index}.jpg', self.raw, content_type='image/jpeg',
                    ),
                })
                for index in range(4)
            ]

        self.assertEqual([response.status_code for response in responses], [200, 200, 200, 200])
        self.assertFalse(responses[0].data['confirmed'])
        self.assertFalse(responses[1].data['confirmed'])
        self.assertFalse(responses[2].data['confirmed'])
        self.assertTrue(responses[3].data['confirmed'])
        self.assertEqual(responses[3].data['continuous_seconds'], 3.0)
        self.assertIsNotNone(responses[3].data['logged_event'])
        self.assertEqual(
            ExamProctoringEvidence.objects.get().event.event_type,
            'gadget_detected',
        )


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

    def test_other_instructor_cannot_read_snapshot(self):
        other = User.objects.create(username='other-teacher', is_staff=True)
        self.client.force_authenticate(other)
        response = self.client.get(
            f'/api/instructor/subjects/{self.exam.subject_id}/exam-sets/{self.exam.pk}'
            f'/submissions/{self.submission.pk}/snapshot/'
        )
        self.assertEqual(response.status_code, 404)
