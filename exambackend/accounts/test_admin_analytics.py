from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import (
    ExamIntegrityReport, ExamProctoringEvent, ExamSet, ExamSubmission,
    Subject, UserProfile,
)


class AdminAnalyticsTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('admin-analytics', 'admin@example.com', 'password')
        self.instructor = User.objects.create_user('instructor-analytics', is_staff=True)
        self.subject = Subject.objects.create(name='Synthetic course', code='SYN', instructor=self.instructor)
        self.exam = ExamSet.objects.create(subject=self.subject, title='Synthetic exam')
        self.client = APIClient()

    def add_attempt(self, email, institute, score, terminated=False):
        student = User.objects.create_user(username=email, email=email)
        UserProfile.objects.create(user=student, role='student', institute=institute, is_enrolled=True)
        submission = ExamSubmission.objects.create(exam_set=self.exam, student_email=email, is_done=True)
        ExamIntegrityReport.objects.create(
            submission=submission, attempt_number=1, integrity_score=Decimal(score),
            summary={'terminated': terminated},
        )
        return submission

    def test_requires_superuser(self):
        self.client.force_authenticate(self.instructor)
        response = self.client.get('/api/admin/analytics/')
        self.assertEqual(response.status_code, 403)

    def test_aggregates_scores_violations_and_distinct_device_types(self):
        low = self.add_attempt('ic@example.com', 'IC', '40.00', terminated=True)
        self.add_attempt('ited@example.com', 'ITED', '90.00')
        ExamProctoringEvent.objects.create(submission=low, event_type='tab_switch')
        ExamProctoringEvent.objects.create(submission=low, event_type='window_blur')
        ExamProctoringEvent.objects.create(submission=low, event_type='gadget_detected', metadata={
            'detections': [{'label': 'cell phone'}, {'label': 'cell phone'}, {'label': 'laptop'}],
        })
        self.client.force_authenticate(self.admin)

        response = self.client.get('/api/admin/analytics/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['summary']['completed_attempts'], 2)
        self.assertEqual(response.data['summary']['average_integrity'], 65.0)
        self.assertEqual(response.data['summary']['flagged_attempts'], 2)
        self.assertEqual(response.data['summary']['terminated_attempts'], 1)
        self.assertEqual(response.data['summary']['recorded_violations'], 2)
        self.assertEqual(response.data['lowest_institute']['code'], 'IC')
        self.assertEqual(response.data['devices'], [
            {'label': 'Cell phone', 'count': 1}, {'label': 'Laptop', 'count': 1},
        ])

    def test_empty_state(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get('/api/admin/analytics/')
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data['summary']['average_integrity'])
        self.assertIsNone(response.data['lowest_institute'])
        self.assertEqual(response.data['devices'], [])
