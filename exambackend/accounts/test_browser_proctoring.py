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

    def test_browser_actions_and_face_warning_are_recorded(self):
        response = self.client.post(
            f'/api/student/exams/{self.exam.pk}/proctoring/events/',
            {'events': [
                {'event_type': 'screen_share_stopped', 'message': 'Screen sharing stopped', 'source': 'screen_share', 'severity': 'critical'},
                {'event_type': 'screenshot_attempt', 'message': 'Screenshot shortcut pressed', 'source': 'keyboard'},
                {'event_type': 'tab_switch', 'message': 'Student switched tabs', 'source': 'visibilitychange'},
                {'event_type': 'split_screen', 'message': 'Student resized the exam window', 'source': 'split_screen'},
                {'event_type': 'extended_monitor', 'message': 'Additional display connected', 'source': 'display_check'},
                {'event_type': 'warning_shown', 'message': 'Face-not-visible notice displayed', 'source': 'face_absence_notice'},
            ]},
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['logged'], 6)
        self.assertEqual(
            list(ExamProctoringEvent.objects.values_list('event_type', flat=True)),
            ['screen_share_stopped', 'screenshot_attempt', 'tab_switch', 'split_screen', 'extended_monitor', 'warning_shown'],
        )
