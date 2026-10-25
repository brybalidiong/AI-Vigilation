from io import BytesIO
from tempfile import TemporaryDirectory

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient

from accounts.models import ExamSet, StudentSet, Subject, UserProfile


class AdminCourseTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('course-admin', 'admin@example.com', 'password')
        self.ic_instructor = self.make_instructor('ic@example.com', 'IC')
        self.second_ic_instructor = self.make_instructor('ic2@example.com', 'IC')
        self.ited_instructor = self.make_instructor('ited@example.com', 'ITED')
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def make_instructor(self, email, institute):
        user = User.objects.create_user(username=email, email=email, is_staff=True)
        UserProfile.objects.create(user=user, role='instructor', institute=institute)
        return user

    def test_only_admin_creates_and_assigns_institute_courses(self):
        payload = {'name': 'Programming', 'code': 'cs101', 'category': 'IC', 'instructor_ids': [self.ic_instructor.id, self.second_ic_instructor.id]}
        self.client.force_authenticate(self.ic_instructor)
        denied = self.client.post('/api/admin/courses/', payload, format='json')
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(self.client.post('/api/instructor/subjects/', payload, format='json').status_code, 403)

        self.client.force_authenticate(self.admin)
        mismatch = self.client.post('/api/admin/courses/', {**payload, 'instructor_ids': [self.ic_instructor.id, self.ited_instructor.id]}, format='json')
        self.assertEqual(mismatch.status_code, 400)
        created = self.client.post('/api/admin/courses/', payload, format='json')
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(created.data['category'], 'IC')
        self.assertEqual(created.data['instructor_ids'], payload['instructor_ids'])
        self.assertEqual(Subject.objects.get(pk=created.data['id']).code, 'CS101')
        self.client.force_authenticate(self.second_ic_instructor)
        self.assertEqual(len(self.client.get('/api/instructor/subjects/').data['subjects']), 1)
        roster = self.client.post(f"/api/instructor/subjects/{created.data['id']}/sets/", {'name': 'Section A'}, format='json')
        self.assertEqual(roster.status_code, 201, roster.data)
        self.assertEqual(self.client.get(f"/api/instructor/subjects/{created.data['id']}/exam-sets/").status_code, 200)
        self.client.force_authenticate(self.ic_instructor)
        self.assertEqual(len(self.client.get(f"/api/instructor/subjects/{created.data['id']}/sets/").data['sets']), 1)

        self.client.force_authenticate(self.admin)
        minor = self.client.post('/api/admin/courses/', {
            'name': 'Ethics', 'code': 'GE101', 'category': 'MINOR', 'instructor_ids': [self.ited_instructor.id, self.ic_instructor.id],
        }, format='json')
        self.assertEqual(minor.status_code, 201, minor.data)
        categories = {row['code']: row['category'] for row in self.client.get('/api/admin/courses/').data['courses']}
        self.assertEqual(categories, {'CS101': 'IC', 'GE101': 'MINOR'})

    def test_reassignment_preserves_exams_and_moves_rosters(self):
        course = Subject.objects.create(name='Networks', code='IT201', category='IC', instructor=self.ic_instructor)
        course.additional_instructors.add(self.second_ic_instructor)
        course.archived_by.add(self.ic_instructor)
        roster = StudentSet.objects.create(name='Section A', subject=course, created_by=self.ic_instructor)
        exam = ExamSet.objects.create(subject=course, title='Midterm')
        result = self.client.patch(f'/api/admin/courses/{course.id}/', {
            'category': 'IC', 'instructor_ids': [self.second_ic_instructor.id],
        }, format='json')
        self.assertEqual(result.status_code, 200, result.data)
        course.refresh_from_db()
        roster.refresh_from_db()
        self.assertEqual(course.instructor_id, self.second_ic_instructor.id)
        self.assertEqual(result.data['instructor_ids'], [self.second_ic_instructor.id])
        self.assertFalse(course.archived_by.filter(pk=self.ic_instructor.pk).exists())
        self.assertEqual(roster.created_by_id, self.second_ic_instructor.id)
        self.client.force_authenticate(self.ic_instructor)
        self.assertEqual(self.client.get(f'/api/instructor/subjects/{course.id}/sets/').status_code, 404)
        self.client.force_authenticate(self.admin)
        self.assertTrue(ExamSet.objects.filter(pk=exam.pk, subject=course).exists())
        self.assertEqual(result.data['exam_count'], 1)
        self.assertEqual(self.client.patch(f'/api/admin/courses/{course.id}/', {
            'category': 'ITED', 'instructor_ids': [self.ic_instructor.id],
        }, format='json').status_code, 400)
        self.assertEqual(self.client.patch(f'/api/admin/instructors/{self.second_ic_instructor.id}/', {
            'action': 'set_institute', 'institute': 'ITED',
        }, format='json').status_code, 409)

    def test_instructor_can_change_only_their_course_banner(self):
        course = Subject.objects.create(name='Networks', code='IT201', category='IC', instructor=self.ic_instructor)
        self.client.force_authenticate(self.ic_instructor)
        media_dir = TemporaryDirectory()
        self.addCleanup(media_dir.cleanup)
        with override_settings(MEDIA_ROOT=media_dir.name):
            image = Image.new('RGB', (16, 16), color='navy')
            stream = BytesIO()
            image.save(stream, format='PNG')
            upload = SimpleUploadedFile('banner.png', stream.getvalue(), content_type='image/png')
            response = self.client.patch(
                f'/api/instructor/subjects/{course.id}/', {'display_photo': upload}, format='multipart',
            )
            self.assertEqual(response.status_code, 200, response.data)
            course.refresh_from_db()
            self.assertTrue(course.display_photo.name.startswith('course_photos/'))
            malformed = self.client.put(f'/api/instructor/subjects/{course.id}/', {}, format='json')
            self.assertEqual(malformed.status_code, 400)
            self.assertTrue(Subject.objects.filter(pk=course.pk).exists())
        self.client.force_authenticate(self.ited_instructor)
        denied = self.client.patch(f'/api/instructor/subjects/{course.id}/', {}, format='multipart')
        self.assertEqual(denied.status_code, 404)

    def test_instructor_archives_only_their_own_view_and_cannot_delete_course(self):
        course = Subject.objects.create(name='Networks', code='IT201', category='IC', instructor=self.ic_instructor)
        course.additional_instructors.add(self.second_ic_instructor)
        roster = StudentSet.objects.create(name='Section A', subject=course, created_by=self.ic_instructor)
        exam = ExamSet.objects.create(subject=course, title='Midterm')
        url = f'/api/instructor/subjects/{course.id}/'

        self.client.force_authenticate(self.ic_instructor)
        self.assertEqual(self.client.delete(url).status_code, 405)
        self.assertEqual(self.client.patch(url, {'archived': 'yes'}, format='json').status_code, 400)
        archived = self.client.patch(url, {'archived': True}, format='json')
        self.assertEqual(archived.status_code, 200, archived.data)
        self.assertTrue(archived.data['is_archived'])
        self.assertTrue(self.client.get('/api/instructor/subjects/').data['subjects'][0]['is_archived'])

        self.client.force_authenticate(self.second_ic_instructor)
        self.assertFalse(self.client.get('/api/instructor/subjects/').data['subjects'][0]['is_archived'])
        self.assertEqual(self.client.get(f'/api/instructor/subjects/{course.id}/exam-sets/').status_code, 200)

        self.client.force_authenticate(self.ited_instructor)
        self.assertEqual(self.client.patch(url, {'archived': True}, format='json').status_code, 404)

        self.client.force_authenticate(self.ic_instructor)
        restored = self.client.patch(url, {'archived': False}, format='json')
        self.assertEqual(restored.status_code, 200, restored.data)
        self.assertFalse(self.client.get('/api/instructor/subjects/').data['subjects'][0]['is_archived'])
        self.assertTrue(Subject.objects.filter(pk=course.pk).exists())
        self.assertTrue(StudentSet.objects.filter(pk=roster.pk).exists())
        self.assertTrue(ExamSet.objects.filter(pk=exam.pk).exists())
