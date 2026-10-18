from asgiref.sync import sync_to_async
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import User
from django.test import TransactionTestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from accounts.models import EnrolledStudent, ExamSet, StudentSet, Subject, UserProfile
from accounts.routing import websocket_urlpatterns


class LiveExamUpdatesTests(TransactionTestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(username='live-instructor', is_staff=True)
        self.subject = Subject.objects.create(
            name='Live Course', code='LIVE', instructor=self.instructor,
        )
        roster = StudentSet.objects.create(
            name='Live Section', subject=self.subject, created_by=self.instructor,
        )
        self.student = User.objects.create_user(
            username='live-student', email='live-student@example.com',
        )
        UserProfile.objects.create(user=self.student, role='student', is_enrolled=True)
        EnrolledStudent.objects.create(email=self.student.email, student_set=roster)
        self.other_student = User.objects.create_user(
            username='other-student', email='other-student@example.com',
        )
        UserProfile.objects.create(user=self.other_student, role='student', is_enrolled=True)
        self.exam = ExamSet.objects.create(subject=self.subject, title='New exam')
        self.instructor_client = APIClient()
        self.instructor_client.force_authenticate(self.instructor)
        self.student_client = APIClient()
        self.student_client.force_authenticate(self.student)

    async def test_publish_updates_enrolled_student_without_page_reload(self):
        communicator = WebsocketCommunicator(
            URLRouter(websocket_urlpatterns),
            f'/ws/student/exams/updates/?token={AccessToken.for_user(self.student)}',
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        try:
            before = await sync_to_async(self.student_client.get)('/api/student/exams/')
            self.assertEqual(before.data['exam_sets'], [])

            publish_url = (
                f'/api/instructor/subjects/{self.subject.pk}/'
                f'exam-sets/{self.exam.pk}/finalize/'
            )
            response = await sync_to_async(self.instructor_client.post)(publish_url)
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(
                await communicator.receive_json_from(timeout=2),
                {'type': 'exam_published'},
            )

            after = await sync_to_async(self.student_client.get)('/api/student/exams/')
            self.assertEqual([row['id'] for row in after.data['exam_sets']], [self.exam.pk])

            response = await sync_to_async(self.instructor_client.post)(publish_url)
            self.assertEqual(response.status_code, 200, response.data)
            self.assertTrue(await communicator.receive_nothing(timeout=0.2))
        finally:
            await communicator.disconnect()

    async def test_student_outside_course_gets_no_publish_event(self):
        communicator = WebsocketCommunicator(
            URLRouter(websocket_urlpatterns),
            f'/ws/student/exams/updates/?token={AccessToken.for_user(self.other_student)}',
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        try:
            publish_url = (
                f'/api/instructor/subjects/{self.subject.pk}/'
                f'exam-sets/{self.exam.pk}/finalize/'
            )
            response = await sync_to_async(self.instructor_client.post)(publish_url)
            self.assertEqual(response.status_code, 200, response.data)
            self.assertTrue(await communicator.receive_nothing(timeout=0.2))
        finally:
            await communicator.disconnect()
