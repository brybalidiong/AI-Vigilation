"""Synthetic checks for the exam blink gate; no student images are used."""

from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.face_liveness import blink_sequence_detected
from accounts.models import EnrolledStudent, ExamSet, StudentSet, Subject, UserProfile


class BlinkSequenceTests(SimpleTestCase):
    def test_open_closed_open_passes(self):
        self.assertTrue(blink_sequence_detected([(.27, .28)] * 4 + [(.07, .08)] * 2 + [(.26, .27)] * 6))

    def test_static_photo_and_one_eye_do_not_pass(self):
        self.assertFalse(blink_sequence_detected([(.27, .28)] * 12))
        self.assertFalse(blink_sequence_detected([(.27, .28)] * 4 + [(.07, .28)] * 2 + [(.27, .28)] * 6))


class VerifyFaceBlinkGateTests(TestCase):
    def setUp(self):
        instructor = User.objects.create_user('instructor', is_staff=True)
        student = User.objects.create_user('student', email='student@example.com')
        UserProfile.objects.create(
            user=student, role='student', is_enrolled=True,
            face_photo='synthetic-id-portrait.jpg', face_encoding='[0.0]',
            face_status=UserProfile.FACE_STATUS_APPROVED, id_verified_at=timezone.now(),
        )
        subject = Subject.objects.create(instructor=instructor, name='Synthetic course', code='SYN')
        roster = StudentSet.objects.create(subject=subject, created_by=instructor, name='Section A')
        EnrolledStudent.objects.create(student_set=roster, email=student.email)
        self.exam = ExamSet.objects.create(subject=subject, title='Synthetic exam', is_final=True)
        self.client = APIClient()
        self.client.force_authenticate(student)

    def _post_frames(self, count):
        frames = [SimpleUploadedFile(f'frame-{index}.jpg', b'synthetic-frame', content_type='image/jpeg') for index in range(count)]
        return self.client.post(f'/api/student/exams/{self.exam.id}/verify-face/', {'blink_frames': frames}, format='multipart')

    def test_still_image_cannot_verify(self):
        with patch('accounts.face_service.verify_face_bytes') as match:
            response = self._post_frames(1)
        self.assertEqual(response.status_code, 400)
        match.assert_not_called()

    def test_face_match_runs_only_after_blink(self):
        with patch('accounts.face_liveness.check_blink_frames', return_value=None), patch('accounts.face_service.verify_face_bytes') as match:
            response = self._post_frames(12)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['verified'])
        match.assert_not_called()

        with patch('accounts.face_liveness.check_blink_frames', return_value=b'synthetic-open-frame'), patch(
            'accounts.face_service.verify_face_bytes', return_value={'verified': True, 'error': None},
        ) as match:
            response = self._post_frames(12)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['verified'])
        match.assert_called_once_with('[0.0]', b'synthetic-open-frame')
