from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import EnrolledStudent, ExamProctoringEvent, ExamSet, StudentSet, Subject


class BrowserProctoringEventTests(TestCase):
    def setUp(self):
        instructor = User.objects.create_user(username='browser-instructor', is_staff=True)
        student = User.objects.create_user(username='browser-student', email='browser@example.com')
        subject = Subject.objects.create(name='Synthetic course', code='SYN', instructor=instructor)
        roster = StudentSet.objects.create(name='Section A', subject=subject, created_by=instructor)
        EnrolledStudent.objects.create(email=student.email, student_set=roster)
        self.exam = ExamSet.objects.create(subject=subject, title='Synthetic exam')
        self.client = APIClient()
        self.client.force_authenticate(student)

    def test_screen_sharing_stop_and_screenshot_attempt_are_recorded(self):
        response = self.client.post(
            f'/api/student/exams/{self.exam.pk}/proctoring/events/',
            {'events': [
                {'event_type': 'screen_share_stopped', 'message': 'Screen sharing stopped', 'source': 'screen_share', 'severity': 'critical'},
                {'event_type': 'screenshot_attempt', 'message': 'Screenshot shortcut pressed', 'source': 'keyboard'},
            ]},
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['logged'], 2)
        self.assertEqual(
            list(ExamProctoringEvent.objects.values_list('event_type', flat=True)),
            ['screen_share_stopped', 'screenshot_attempt'],
        )
