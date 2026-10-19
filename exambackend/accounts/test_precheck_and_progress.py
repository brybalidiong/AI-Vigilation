from unittest.mock import patch

import numpy as np
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from accounts.face_service import detect_face_position_bytes
from accounts.models import (
    EnrolledStudent, ExamProctoringEvent, ExamSet, ExamSubmission,
    StudentSet, Subject, UserProfile,
)


class FacePositionTests(SimpleTestCase):
    def test_normalizes_one_face_and_rejects_multiple(self):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        detector = type('Detector', (), {'detect': lambda self, image: (
            None, np.array([[160, 120, 320, 240, *([0] * 11)]], dtype=np.float32),
        )})()
        with patch('accounts.face_service._load_image_bytes', return_value=frame), patch(
            'accounts.face_service._get_detector', return_value=detector,
        ):
            result = detect_face_position_bytes(b'synthetic frame')
        self.assertEqual(result['label'], 'normal')
        self.assertEqual(result['face_bbox'], [0.25, 0.25, 0.75, 0.75])


class PrecheckAndProgressTests(TestCase):
    def setUp(self):
        self.instructor = User.objects.create_user('instructor', email='instructor@example.com', is_staff=True)
        self.student = User.objects.create_user('student', email='student@example.com')
        UserProfile.objects.create(user=self.student, role='student', is_enrolled=True)
        self.subject = Subject.objects.create(instructor=self.instructor, name='Synthetic course', code='SYN')
        self.roster = StudentSet.objects.create(subject=self.subject, created_by=self.instructor, name='Section A')
        EnrolledStudent.objects.create(student_set=self.roster, email=self.student.email)
        self.exam = ExamSet.objects.create(subject=self.subject, title='Synthetic exam', is_final=True)
        self.client = APIClient()

    def test_face_precheck_requires_student_and_does_not_start_attempt(self):
        url = f'/api/student/exams/{self.exam.id}/precheck-face/'
        image = SimpleUploadedFile('frame.jpg', b'synthetic frame', content_type='image/jpeg')
        self.client.force_authenticate(self.student)
        with patch('accounts.face_service.detect_face_position_bytes', return_value={
            'label': 'normal', 'face_detected': True, 'face_bbox': [0.2, 0.2, 0.8, 0.8],
        }):
            response = self.client.post(url, {'image': image}, format='multipart')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['face_bbox'], [0.2, 0.2, 0.8, 0.8])
        self.assertFalse(ExamSubmission.objects.exists())

        self.client.force_authenticate(self.instructor)
        response = self.client.post(url, {'image': SimpleUploadedFile('frame.jpg', b'x')}, format='multipart')
        self.assertEqual(response.status_code, 403)

    def test_progress_includes_only_current_attempt_gadget_flags(self):
        submission = ExamSubmission.objects.create(
            exam_set=self.exam, student_email=self.student.email, attempt_count=2, is_done=True,
        )
        ExamProctoringEvent.objects.create(
            submission=submission, attempt_number=1, event_type=ExamProctoringEvent.EVENT_GADGET_DETECTED,
        )
        ExamProctoringEvent.objects.create(
            submission=submission, attempt_number=2, event_type=ExamProctoringEvent.EVENT_GADGET_DETECTED,
        )
        self.client.force_authenticate(self.instructor)
        response = self.client.get(f'/api/instructor/subjects/{self.subject.id}/exam-progress/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['progress'][0]['gadget_detection_count'], 1)
