from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import (
    EnrolledStudent, ExamIntegrityReport, ExamProctoringEvent, ExamSet,
    ExamSubmission, StudentSet, Subject, UserProfile,
)


class AdminAnalyticsTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('admin-analytics', 'admin@example.com', 'password')
        self.instructor = User.objects.create_user('instructor-analytics', is_staff=True)
        self.subject = Subject.objects.create(name='Synthetic course', code='SYN', instructor=self.instructor)
        self.exam = ExamSet.objects.create(subject=self.subject, title='Synthetic exam')
        self.client = APIClient()

    def add_attempt(self, email, institute, score, terminated=False, model_code=''):
        student = User.objects.create_user(username=email, email=email)
        UserProfile.objects.create(user=student, role='student', institute=institute, is_enrolled=True)
        submission = ExamSubmission.objects.create(exam_set=self.exam, student_email=email, is_done=True)
        ExamIntegrityReport.objects.create(
            submission=submission, attempt_number=1, integrity_score=Decimal(score),
            summary={'terminated': terminated, 'gaze_model_code': model_code},
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
        self.assertTrue(all(row['average_integrity'] is None for row in response.data['gaze_models']))

    def test_integrity_by_model_excludes_unattributed_history(self):
        self.add_attempt('efficient-a@example.com', 'IC', '60.00', model_code='efficientnet')
        self.add_attempt('efficient-b@example.com', 'IC', '80.00', model_code='efficientnet')
        self.add_attempt('mobile@example.com', 'ITED', '90.00', model_code='mobilenetv2')
        self.add_attempt('historical@example.com', 'IASS', '50.00')
        self.client.force_authenticate(self.admin)

        response = self.client.get('/api/admin/analytics/')

        self.assertEqual(response.status_code, 200, response.data)
        models = {row['code']: row for row in response.data['gaze_models']}
        self.assertEqual((models['efficientnet']['average_integrity'], models['efficientnet']['attempts']), (70.0, 2))
        self.assertEqual((models['mobilenetv2']['average_integrity'], models['mobilenetv2']['attempts']), (90.0, 1))
        self.assertEqual((models['resnet50v2']['average_integrity'], models['resnet50v2']['attempts']), (None, 0))
        self.assertEqual(response.data['unattributed_attempts'], 1)

    def test_exam_start_records_model_and_report_keeps_it_per_attempt(self):
        student = User.objects.create_user('model-student', email='model-student@example.com')
        UserProfile.objects.create(user=student, role='student', institute='IC', is_enrolled=True)
        roster = StudentSet.objects.create(name='Model section', subject=self.subject, created_by=self.instructor)
        EnrolledStudent.objects.create(email=student.email, student_set=roster)
        self.exam.is_final = True
        self.exam.max_attempts = 2
        self.exam.save(update_fields=['is_final', 'max_attempts'])
        self.client.force_authenticate(student)
        url = f'/api/student/exams/{self.exam.pk}/questions/'

        with patch('accounts.gaze_service.selected_gaze_model_code', return_value='mobilenetv2'):
            response = self.client.get(url)
        self.assertEqual(response.status_code, 200, response.data)
        submission = ExamSubmission.objects.get(exam_set=self.exam, student_email=student.email)
        self.assertEqual(submission.gaze_model_code, 'mobilenetv2')
        from accounts.views import _build_integrity_report
        first_report = _build_integrity_report(submission)
        self.assertEqual(first_report.summary['gaze_model_code'], 'mobilenetv2')

        submission.is_done = True
        submission.save(update_fields=['is_done'])
        with patch('accounts.gaze_service.selected_gaze_model_code', return_value='resnet50v2'):
            response = self.client.get(url)
        self.assertEqual(response.status_code, 200, response.data)
        submission.refresh_from_db()
        self.assertEqual(submission.gaze_model_code, 'resnet50v2')
        self.assertEqual(submission.attempt_count, 2)
        self.assertEqual(ExamIntegrityReport.objects.get(
            submission=submission, attempt_number=1,
        ).summary['gaze_model_code'], 'mobilenetv2')

    def test_early_proctoring_event_records_model_before_questions_open(self):
        student = User.objects.create_user('early-student', email='early-student@example.com')
        UserProfile.objects.create(user=student, role='student', institute='IC', is_enrolled=True)
        roster = StudentSet.objects.create(name='Early section', subject=self.subject, created_by=self.instructor)
        EnrolledStudent.objects.create(email=student.email, student_set=roster)
        self.client.force_authenticate(student)

        with patch('accounts.gaze_service.selected_gaze_model_code', return_value='resnet50v2'):
            response = self.client.post(
                f'/api/student/exams/{self.exam.pk}/proctoring/events/',
                {'event_type': ExamProctoringEvent.EVENT_EXAM_STARTED}, format='json',
            )
        self.assertEqual(response.status_code, 201, response.data)
        submission = ExamSubmission.objects.get(exam_set=self.exam, student_email=student.email)
        self.assertEqual(submission.gaze_model_code, 'resnet50v2')
