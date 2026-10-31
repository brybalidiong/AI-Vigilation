from django.contrib.auth.models import User
from django.apps import apps
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import SimpleTestCase, TestCase, override_settings
from openpyxl import Workbook
from rest_framework.test import APIClient
from decimal import Decimal
from datetime import timedelta
from io import BytesIO
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import patch
from tempfile import TemporaryDirectory
import cv2
import numpy as np
from django.utils import timezone

from accounts.grading import grade_question
from accounts.models import (
    EnrolledStudent, ExamQuestion, ExamSet, ExamSubmission, QuestionBankItem, StudentAnswer,
    StudentSet, Subject, SubjectEnrollment, UserProfile,
)
from accounts.student_id_service import StudentIdError, _name_matches, verify_student_id


class StudentIdReadingTests(SimpleTestCase):
    def setUp(self):
        image = np.zeros((1000, 700, 3), dtype=np.uint8)
        self.image = cv2.imencode('.jpg', image)[1].tobytes()

    def test_middle_initial_does_not_prevent_exact_first_and_last_name_match(self):
        self.assertTrue(_name_matches('ALEX Q. REYES', 'Alex', 'Reyes'))
        self.assertFalse(_name_matches('ALEX Q. SANTOS', 'Alex', 'Reyes'))
        self.assertFalse(_name_matches('ALEX REYES AND SANTOS', 'Alex', 'Reyes'))

    @patch('accounts.student_id_service._get_face_features')
    @patch('accounts.student_id_service._read_text')
    def test_matching_dnsc_student_id_extracts_portrait(self, read_text, get_features):
        read_text.side_effect = ['DAVAO DEL NORTE STATE COLLEGE', 'STUDENT', 'ALEX Q. REYES']
        get_features.return_value = np.array([[0.1, 0.2]], dtype=np.float32)
        self.assertEqual(len(verify_student_id(self.image, 'Alex', 'Reyes')), 2)
        get_features.assert_called_once()

    @patch('accounts.student_id_service._get_face_features')
    @patch('accounts.student_id_service._read_text')
    def test_plain_ocr_recovers_stylized_header_and_student_label(self, read_text, get_features):
        read_text.side_effect = [
            'STATE COLLE G', 'DAVAO DEL NORTE STATE CO LLEG',
            'STU DENT', 'STUDENT', 'ALEX Q. REYES',
        ]
        get_features.return_value = np.array([[0.1, 0.2]], dtype=np.float32)
        self.assertEqual(len(verify_student_id(self.image, 'Alex', 'Reyes')), 2)
        self.assertEqual(read_text.call_count, 5)

    @patch('accounts.student_id_service._get_face_features')
    @patch('accounts.student_id_service._read_text')
    def test_mismatched_name_rejects_before_portrait_is_used(self, read_text, get_features):
        read_text.side_effect = ['DAVAO DEL NORTE STATE COLLEGE', 'STUDENT', 'ALEX Q. SANTOS', 'ALEX Q. SANTOS']
        with self.assertRaises(StudentIdError):
            verify_student_id(self.image, 'Alex', 'Reyes')
        get_features.assert_not_called()

    @patch('accounts.student_id_service._read_text', return_value='SCHOOL CARD')
    def test_other_school_is_rejected(self, _read_text):
        with self.assertRaises(StudentIdError):
            verify_student_id(self.image, 'Alex', 'Reyes')

    @patch('accounts.student_id_service._read_text')
    def test_missing_student_label_is_rejected(self, read_text):
        read_text.side_effect = ['DAVAO DEL NORTE STATE COLLEGE', 'FACULTY', 'FACULTY']
        with self.assertRaises(StudentIdError):
            verify_student_id(self.image, 'Alex', 'Reyes')

    @patch('accounts.student_id_service._get_face_features', return_value=None)
    @patch('accounts.student_id_service._read_text')
    def test_unreadable_portrait_is_rejected(self, read_text, _features):
        read_text.side_effect = ['DAVAO DEL NORTE STATE COLLEGE', 'STUDENT', 'ALEX Q. REYES']
        with self.assertRaises(StudentIdError):
            verify_student_id(self.image, 'Alex', 'Reyes')


class StudentIdUploadTests(TestCase):
    def setUp(self):
        self.temp_media = TemporaryDirectory()
        self.addCleanup(self.temp_media.cleanup)
        self.media_override = override_settings(MEDIA_ROOT=self.temp_media.name)
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)
        self.student = User.objects.create_user(
            username='alex@dnsc.edu.ph', email='alex@dnsc.edu.ph',
            first_name='Alex', last_name='Reyes',
        )
        UserProfile.objects.create(user=self.student, role='student', is_enrolled=True)
        self.client = APIClient()
        self.client.force_authenticate(self.student)

    def test_student_cannot_change_account_name_before_upload(self):
        result = self.client.post('/api/auth/me/update/', {'first_name': 'Someone'}, format='multipart')
        self.assertEqual(result.status_code, 400)
        self.student.refresh_from_db()
        self.assertEqual(self.student.first_name, 'Alex')

    @patch('accounts.student_id_service.verify_student_id', return_value=[0.1, 0.2])
    def test_matching_id_is_automatically_approved(self, verify):
        upload = SimpleUploadedFile('synthetic.jpg', b'synthetic-image', content_type='image/jpeg')
        result = self.client.post('/api/auth/me/update/', {'face_photo': upload}, format='multipart')
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(result.data['user']['face_status'], 'approved')
        self.student.profile.refresh_from_db()
        self.assertIsNotNone(self.student.profile.id_verified_at)
        verify.assert_called_once_with(b'synthetic-image', 'Alex', 'Reyes')

    @patch('accounts.student_id_service.verify_student_id', side_effect=StudentIdError('Name mismatch.'))
    def test_rejected_id_does_not_change_verification(self, _verify):
        upload = SimpleUploadedFile('synthetic.jpg', b'synthetic-image', content_type='image/jpeg')
        result = self.client.post('/api/auth/me/update/', {'face_photo': upload}, format='multipart')
        self.assertEqual(result.status_code, 400)
        self.student.profile.refresh_from_db()
        self.assertIsNone(self.student.profile.id_verified_at)
        self.assertFalse(self.student.profile.face_photo)


class AdminAccessWorkflowTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='admin-workflow', is_superuser=True)
        self.instructor = User.objects.create_user(
            username='instructor@dnsc.edu.ph', email='instructor@dnsc.edu.ph', is_staff=True,
        )
        UserProfile.objects.create(user=self.instructor, role='instructor')
        self.subject = Subject.objects.create(
            name='Preserved Course', code='KEEP', instructor=self.instructor,
        )
        self.exam = ExamSet.objects.create(subject=self.subject, title='Preserved Exam', is_final=True)
        self.student = User.objects.create_user(
            username='student@dnsc.edu.ph', email='student@dnsc.edu.ph',
        )
        UserProfile.objects.create(user=self.student, role='student', is_enrolled=True)
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def test_instructor_deactivation_keeps_courses_and_can_be_restored(self):
        url = f'/api/admin/instructors/{self.instructor.pk}/'
        response = self.client.patch(url, {'is_active': False}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.instructor.refresh_from_db()
        self.assertFalse(self.instructor.is_active)
        self.assertFalse(self.instructor.is_staff)
        self.assertTrue(Subject.objects.filter(pk=self.subject.pk).exists())
        self.assertTrue(ExamSet.objects.filter(pk=self.exam.pk).exists())
        listed = self.client.get('/api/admin/instructors/')
        self.assertTrue(any(row['id'] == self.instructor.pk and not row['is_active'] for row in listed.data['instructors']))

        response = self.client.patch(url, {'is_active': True}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.instructor.refresh_from_db()
        self.assertTrue(self.instructor.is_active)
        self.assertTrue(self.instructor.is_staff)

    @override_settings(ALLOWED_SCHOOL_DOMAIN='dnsc.edu.ph')
    def test_admin_edits_instructor_email_without_changing_courses(self):
        url = f'/api/admin/instructors/{self.instructor.pk}/'
        for email, expected_status in (
            ('not-an-email', 400),
            ('other@example.com', 400),
            (self.student.email, 409),
        ):
            response = self.client.patch(url, {'action': 'set_email', 'email': email}, format='json')
            self.assertEqual(response.status_code, expected_status, response.data)
        response = self.client.patch(url, {
            'action': 'set_email', 'email': 'New.Instructor@dnsc.edu.ph',
        }, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.instructor.refresh_from_db()
        self.assertEqual(self.instructor.email, 'new.instructor@dnsc.edu.ph')
        self.assertEqual(self.instructor.username, self.instructor.email)
        self.assertTrue(Subject.objects.filter(pk=self.subject.pk, instructor=self.instructor).exists())

    def test_deleting_instructor_requires_course_reassignment_and_preserves_roster(self):
        url = f'/api/admin/instructors/{self.instructor.pk}/'
        roster = StudentSet.objects.create(name='Synthetic roster', created_by=self.instructor)
        blocked = self.client.delete(url)
        self.assertEqual(blocked.status_code, 409, blocked.data)
        self.assertTrue(User.objects.filter(pk=self.instructor.pk).exists())
        self.assertTrue(ExamSet.objects.filter(pk=self.exam.pk).exists())
        replacement = User.objects.create_user(username='replacement@dnsc.edu.ph', is_staff=True)
        self.subject.instructor = replacement
        self.subject.save(update_fields=['instructor'])
        deleted = self.client.delete(url)
        self.assertEqual(deleted.status_code, 204)
        self.assertFalse(User.objects.filter(pk=self.instructor.pk).exists())
        self.assertTrue(ExamSet.objects.filter(pk=self.exam.pk).exists())
        roster.refresh_from_db()
        self.assertIsNone(roster.created_by_id)

    def test_deleting_additional_instructor_requires_reassignment(self):
        additional = User.objects.create_user(username='additional@dnsc.edu.ph', is_staff=True)
        UserProfile.objects.create(user=additional, role='instructor')
        self.subject.additional_instructors.add(additional)
        response = self.client.delete(f'/api/admin/instructors/{additional.pk}/')
        self.assertEqual(response.status_code, 409, response.data)
        self.assertTrue(User.objects.filter(pk=additional.pk).exists())

    def test_non_admin_cannot_edit_or_delete_instructor(self):
        self.client.force_authenticate(self.student)
        url = f'/api/admin/instructors/{self.instructor.pk}/'
        self.assertEqual(self.client.patch(url, {
            'action': 'set_email', 'email': 'changed@dnsc.edu.ph',
        }, format='json').status_code, 403)
        self.assertEqual(self.client.delete(url).status_code, 403)

    def test_student_enrollment_can_be_disabled_and_restored(self):
        url = f'/api/admin/students/{self.student.pk}/'
        for enabled in (False, True):
            response = self.client.patch(url, {
                'action': 'set_enrollment', 'is_enrolled': enabled,
            }, format='json')
            self.assertEqual(response.status_code, 200, response.data)
            self.student.profile.refresh_from_db()
            self.student.refresh_from_db()
            self.assertEqual(self.student.profile.is_enrolled, enabled)
            self.assertEqual(self.student.is_active, enabled)

    def test_admin_deletes_student_access_but_retains_exam_history(self):
        roster = StudentSet.objects.create(name='Synthetic section', subject=self.subject)
        EnrolledStudent.objects.create(email=self.student.email, student_set=roster)
        SubjectEnrollment.objects.create(email=self.student.email, subject=self.subject)
        submission = ExamSubmission.objects.create(
            exam_set=self.exam, student_email=self.student.email, is_done=True,
        )
        response = self.client.delete(f'/api/admin/students/{self.student.pk}/')
        self.assertEqual(response.status_code, 204)
        self.assertFalse(User.objects.filter(pk=self.student.pk).exists())
        self.assertFalse(EnrolledStudent.objects.filter(email=self.student.email).exists())
        self.assertFalse(SubjectEnrollment.objects.filter(email=self.student.email).exists())
        self.assertTrue(ExamSubmission.objects.filter(pk=submission.pk).exists())
        self.assertFalse(any(
            row['id'] == self.student.pk
            for row in self.client.get('/api/admin/students/').data['students']
        ))

    def test_only_admin_can_delete_student_account(self):
        url = f'/api/admin/students/{self.student.pk}/'
        self.client.force_authenticate(self.instructor)
        self.assertEqual(self.client.delete(url).status_code, 403)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.delete(
            f'/api/admin/students/{self.instructor.pk}/',
        ).status_code, 404)

    def test_face_reupload_can_be_turned_off_again(self):
        profile = self.student.profile
        profile.face_photo = 'face_photos/synthetic.jpg'
        profile.face_status = UserProfile.FACE_STATUS_APPROVED
        profile.id_verified_at = timezone.now()
        profile.save(update_fields=['face_photo', 'face_status', 'id_verified_at'])
        url = f'/api/admin/students/{self.student.pk}/'
        first = self.client.patch(url, {'action': 'toggle_reupload'}, format='json')
        self.assertEqual(first.status_code, 200, first.data)
        self.assertTrue(first.data['face_reupload_allowed'])
        self.assertEqual(first.data['face_status'], UserProfile.FACE_STATUS_NONE)
        second = self.client.patch(url, {'action': 'toggle_reupload'}, format='json')
        self.assertEqual(second.status_code, 200, second.data)
        self.assertFalse(second.data['face_reupload_allowed'])
        self.assertEqual(second.data['face_status'], UserProfile.FACE_STATUS_APPROVED)

    def test_legacy_photo_cannot_be_manually_approved(self):
        profile = self.student.profile
        profile.face_pending_photo = 'face_pending/synthetic.jpg'
        profile.save(update_fields=['face_pending_photo'])
        response = self.client.patch(
            f'/api/admin/students/{self.student.pk}/',
            {'action': 'approve_face'}, format='json',
        )
        self.assertEqual(response.status_code, 400, response.data)
        profile.refresh_from_db()
        self.assertIsNone(profile.id_verified_at)
        self.assertTrue(profile.face_pending_photo)

    @override_settings(ALLOWED_SCHOOL_DOMAIN='dnsc.edu.ph')
    def test_admin_name_correction_requires_new_id(self):
        self.student.first_name = 'Alex'
        self.student.last_name = 'Reyes'
        self.student.save(update_fields=['first_name', 'last_name'])
        profile = self.student.profile
        profile.face_photo = 'face_photos/synthetic.jpg'
        profile.face_encoding = '[0.1, 0.2]'
        profile.face_status = UserProfile.FACE_STATUS_APPROVED
        profile.id_verified_at = timezone.now()
        profile.save(update_fields=['face_photo', 'face_encoding', 'face_status', 'id_verified_at'])
        response = self.client.post('/api/admin/students/', {
            'email': self.student.email, 'first_name': 'Alex', 'last_name': 'Santos', 'institute': 'IC',
        }, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        profile.refresh_from_db()
        self.assertIsNone(profile.id_verified_at)
        self.assertIsNone(profile.face_encoding)
        self.assertEqual(profile.face_status, UserProfile.FACE_STATUS_NONE)

    def test_admin_rejects_stored_face_photo_through_storage(self):
        profile = self.student.profile
        profile.face_pending_photo = 'face_pending/synthetic.jpg'
        profile.save(update_fields=['face_pending_photo'])
        with patch.object(type(profile.face_pending_photo), 'delete') as delete:
            response = self.client.patch(
                f'/api/admin/students/{self.student.pk}/',
                {'action': 'reject_face'}, format='json',
            )
        self.assertEqual(response.status_code, 200, response.data)
        delete.assert_called_once_with(save=False)

    def test_non_admin_cannot_change_access(self):
        self.client.force_authenticate(self.student)
        response = self.client.patch(
            f'/api/admin/instructors/{self.instructor.pk}/', {'is_active': False}, format='json',
        )
        self.assertEqual(response.status_code, 403)

    @override_settings(ALLOWED_SCHOOL_DOMAIN='dnsc.edu.ph')
    def test_registration_requires_valid_institute_and_lists_assignment(self):
        for url in ('/api/admin/instructors/', '/api/admin/students/'):
            email = ('new-instructor' if 'instructors' in url else 'new-student') + '@dnsc.edu.ph'
            missing = self.client.post(url, {'email': email}, format='json')
            self.assertEqual(missing.status_code, 400, missing.data)
            invalid = self.client.post(url, {'email': email, 'institute': 'OTHER'}, format='json')
            self.assertEqual(invalid.status_code, 400, invalid.data)
            self.assertFalse(User.objects.filter(username=email).exists())

            created = self.client.post(url, {'email': email, 'institute': 'IC'}, format='json')
            self.assertEqual(created.status_code, 201, created.data)
            self.assertEqual(created.data['institute'], 'IC')
            listed = self.client.get(url)
            rows = listed.data['instructors' if 'instructors' in url else 'students']
            self.assertEqual(next(row for row in rows if row['id'] == created.data['id'])['institute'], 'IC')
            self.assertEqual(User.objects.get(username=email).profile.institute, 'IC')

    def test_admin_can_assign_existing_accounts_to_institutes(self):
        for account, url in (
            (self.instructor, f'/api/admin/instructors/{self.instructor.pk}/'),
            (self.student, f'/api/admin/students/{self.student.pk}/'),
        ):
            invalid = self.client.patch(url, {'action': 'set_institute', 'institute': 'OTHER'}, format='json')
            self.assertEqual(invalid.status_code, 400, invalid.data)
            updated = self.client.patch(url, {'action': 'set_institute', 'institute': 'ITED'}, format='json')
            self.assertEqual(updated.status_code, 200, updated.data)
            account.profile.refresh_from_db()
            self.assertEqual(account.profile.institute, 'ITED')
            self.client.force_authenticate(self.student)
            denied = self.client.patch(url, {'action': 'set_institute', 'institute': 'IASS'}, format='json')
            self.assertEqual(denied.status_code, 403)
            self.client.force_authenticate(self.admin)

    @override_settings(ALLOWED_SCHOOL_DOMAIN='dnsc.edu.ph')
    def test_reenrolling_student_updates_institute(self):
        response = self.client.post('/api/admin/students/', {
            'email': self.student.email, 'institute': 'ILEGG',
        }, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.student.profile.refresh_from_db()
        self.assertEqual(self.student.profile.institute, 'ILEGG')

    def test_admin_login_uses_database_password_and_requires_superuser(self):
        self.admin.is_staff = True
        self.admin.set_password('synthetic-admin-password')
        self.admin.save(update_fields=['is_staff', 'password'])
        client = APIClient()
        url = '/api/auth/admin/login/'

        wrong = client.post(url, {'username': self.admin.username, 'password': 'wrong'}, format='json')
        self.assertEqual(wrong.status_code, 401)
        self.assertFalse(UserProfile.objects.filter(user=self.admin).exists())

        success = client.post(url, {
            'username': self.admin.username, 'password': 'synthetic-admin-password',
        }, format='json')
        self.assertEqual(success.status_code, 200, success.data)
        self.assertIn('access_token', success.data)
        self.assertEqual(self.admin.profile.role, 'admin')

        self.admin.is_staff = False
        self.admin.save(update_fields=['is_staff'])
        denied = client.post(url, {
            'username': self.admin.username, 'password': 'synthetic-admin-password',
        }, format='json')
        self.assertEqual(denied.status_code, 401)

        self.student.set_password('synthetic-student-password')
        self.student.save(update_fields=['password'])
        student_login = client.post(url, {
            'username': self.student.username, 'password': 'synthetic-student-password',
        }, format='json')
        self.assertEqual(student_login.status_code, 401)
        self.student.refresh_from_db()
        self.assertFalse(self.student.is_superuser)

    def test_legacy_admin_migration_hashes_password_without_promoting_other_users(self):
        migration = import_module('accounts.migrations.0035_move_admin_credentials_to_database')
        schema_editor = SimpleNamespace(connection=connection)
        self.admin.is_staff = True
        self.admin.save(update_fields=['is_staff'])
        with patch.dict('os.environ', {
            'ADMIN_USERNAME': self.admin.username,
            'ADMIN_PASSWORD': 'synthetic-legacy-secret',
        }):
            migration.move_admin_credentials(apps, schema_editor)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password('synthetic-legacy-secret'))
        self.assertEqual(self.admin.profile.role, 'admin')

        with patch.dict('os.environ', {
            'ADMIN_USERNAME': self.student.username,
            'ADMIN_PASSWORD': 'synthetic-legacy-secret',
        }):
            with self.assertRaises(RuntimeError):
                migration.move_admin_credentials(apps, schema_editor)
        self.student.refresh_from_db()
        self.assertFalse(self.student.is_superuser)

        with patch.dict('os.environ', {
            'ADMIN_USERNAME': 'new-admin',
            'ADMIN_PASSWORD': 'synthetic-new-secret',
        }):
            migration.move_admin_credentials(apps, schema_editor)
        new_admin = User.objects.get(username='new-admin')
        self.assertTrue(new_admin.is_staff and new_admin.is_superuser)
        self.assertTrue(new_admin.check_password('synthetic-new-secret'))
        self.assertEqual(new_admin.profile.role, 'admin')

    @override_settings(ALLOWED_SCHOOL_DOMAIN='dnsc.edu.ph')
    def test_register_instructor_does_not_promote_existing_student(self):
        response = self.client.post('/api/admin/instructors/', {
            'email': self.student.email, 'first_name': 'Student', 'institute': 'IC',
        }, format='json')
        self.assertEqual(response.status_code, 409, response.data)
        self.student.refresh_from_db()
        self.assertFalse(self.student.is_staff)
        self.assertEqual(self.student.profile.role, 'student')

    @override_settings(ALLOWED_SCHOOL_DOMAIN='dnsc.edu.ph')
    def test_enroll_student_does_not_convert_existing_instructor(self):
        response = self.client.post('/api/admin/students/', {
            'email': self.instructor.email, 'institute': 'IC',
        }, format='json')
        self.assertEqual(response.status_code, 409, response.data)
        self.instructor.refresh_from_db()
        self.assertTrue(self.instructor.is_staff)
        self.assertEqual(self.instructor.profile.role, 'instructor')

    @override_settings(ALLOWED_SCHOOL_DOMAIN='dnsc.edu.ph')
    def test_deactivated_instructor_cannot_sign_in(self):
        self.instructor.is_active = False
        self.instructor.save(update_fields=['is_active'])
        with patch('accounts.views.firebase_auth.verify_id_token', return_value={
            'email': self.instructor.email, 'name': 'Instructor Example',
        }):
            response = self.client.post('/api/auth/google/', {'token': 'synthetic-token'})
        self.assertEqual(response.status_code, 403, response.data)
        self.assertNotIn('access_token', response.data)


@override_settings(ALLOWED_SCHOOL_DOMAIN='dnsc.edu.ph')
class ExcelEnrollmentImportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.instructor = User.objects.create_user(
            username='excel-instructor', is_staff=True,
        )
        cls.subject = Subject.objects.create(
            name='Excel Imports', code='XLSX', instructor=cls.instructor,
        )
        cls.roster = StudentSet.objects.create(
            name='Section Excel', subject=cls.subject, created_by=cls.instructor,
        )
        for username in ('new.student', 'existing.student'):
            user = User.objects.create_user(
                username=username, email=f'{username}@dnsc.edu.ph',
            )
            UserProfile.objects.create(user=user, role='student', is_enrolled=True)
        EnrolledStudent.objects.create(
            email='existing.student@dnsc.edu.ph', student_set=cls.roster,
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.instructor)
        self.url = f'/api/instructor/sets/{self.roster.pk}/enroll-bulk/'

    @staticmethod
    def workbook_upload(rows, filename='students.xlsx'):
        workbook = Workbook()
        worksheet = workbook.active
        for row in rows:
            worksheet.append(row)
        output = BytesIO()
        workbook.save(output)
        workbook.close()
        return SimpleUploadedFile(
            filename,
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )

    def test_imports_email_column_and_reports_row_results(self):
        upload = self.workbook_upload([
            ['Student Name', 'Student Email'],
            ['New Student', 'NEW.STUDENT@DNSC.EDU.PH'],
            ['Existing Student', 'existing.student@dnsc.edu.ph'],
            ['Outside Domain', 'outsider@example.com'],
            ['Unknown Student', 'unknown@dnsc.edu.ph'],
        ])

        response = self.client.post(self.url, {'file': upload}, format='multipart')

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['file_name'], 'students.xlsx')
        self.assertEqual(response.data['rows_processed'], 4)
        self.assertEqual(
            response.data['added'],
            [{'id': EnrolledStudent.objects.get(email='new.student@dnsc.edu.ph').id,
              'email': 'new.student@dnsc.edu.ph'}],
        )
        self.assertEqual(
            response.data['skipped_duplicates'],
            ['existing.student@dnsc.edu.ph'],
        )
        self.assertEqual([item['row'] for item in response.data['errors']], [4, 5])

    def test_rejects_workbook_without_email_header(self):
        upload = self.workbook_upload([['Name', 'Student Number'], ['Test', '123']])

        response = self.client.post(self.url, {'file': upload}, format='multipart')

        self.assertEqual(response.status_code, 400)
        self.assertIn('No email column', response.data['error'])

    def test_rejects_non_xlsx_upload(self):
        upload = SimpleUploadedFile('students.csv', b'Email\nstudent@dnsc.edu.ph')

        response = self.client.post(self.url, {'file': upload}, format='multipart')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['error'], 'Only .xlsx Excel files are supported.')


@override_settings(ALLOWED_SCHOOL_DOMAIN='dnsc.edu.ph')
class CourseEnrollmentUniquenessTests(TestCase):
    def setUp(self):
        self.lead = User.objects.create_user('lead-instructor', is_staff=True)
        self.other = User.objects.create_user('other-instructor', is_staff=True)
        self.subject = Subject.objects.create(name='Shared Course', code='SHARED', instructor=self.lead)
        self.subject.additional_instructors.add(self.other)
        self.first_set = StudentSet.objects.create(
            name='Section A', subject=self.subject, created_by=self.lead,
        )
        self.second_set = StudentSet.objects.create(
            name='Section B', subject=self.subject, created_by=self.other,
        )
        student = User.objects.create_user('shared-student', email='shared.student@dnsc.edu.ph')
        UserProfile.objects.create(user=student, role='student', is_enrolled=True)
        self.email = student.email
        self.client = APIClient()
        self.client.force_authenticate(self.lead)

    def test_other_instructor_cannot_add_student_to_second_course_roster(self):
        url = f'/api/instructor/subjects/{self.subject.pk}/students/'
        first = self.client.post(url, {
            'email': self.email, 'student_set_id': self.first_set.pk,
        }, format='json')
        self.assertEqual(first.status_code, 201, first.data)

        self.client.force_authenticate(self.other)
        duplicate = self.client.post(url, {
            'email': self.email.upper(), 'student_set_id': self.second_set.pk,
        }, format='json')
        self.assertEqual(duplicate.status_code, 409, duplicate.data)
        self.assertIn('Section A', duplicate.data['error'])
        self.assertEqual(EnrolledStudent.objects.filter(student_set__subject=self.subject).count(), 1)

    def test_bulk_and_general_enrollment_skip_second_course_roster(self):
        EnrolledStudent.objects.create(email=self.email, student_set=self.first_set)
        self.client.force_authenticate(self.other)
        bulk = self.client.post(
            f'/api/instructor/sets/{self.second_set.pk}/enroll-bulk/',
            {'emails': [self.email]}, format='json',
        )
        self.assertEqual(bulk.status_code, 200, bulk.data)
        self.assertEqual(bulk.data['added'], [])
        self.assertEqual(bulk.data['skipped_duplicates'], [self.email])

        general = self.client.post('/api/instructor/students/', {
            'email': self.email, 'student_set_id': self.second_set.pk,
        }, format='json')
        self.assertEqual(general.status_code, 409, general.data)
        self.assertEqual(EnrolledStudent.objects.filter(student_set__subject=self.subject).count(), 1)

    def test_student_can_move_to_another_roster_after_removal(self):
        enrollment = EnrolledStudent.objects.create(email=self.email, student_set=self.first_set)
        self.client.force_authenticate(self.other)
        remove = self.client.delete(
            f'/api/instructor/subjects/{self.subject.pk}/students/{enrollment.pk}/',
        )
        self.assertEqual(remove.status_code, 204)
        add = self.client.post(f'/api/instructor/subjects/{self.subject.pk}/students/', {
            'email': self.email, 'student_set_id': self.second_set.pk,
        }, format='json')
        self.assertEqual(add.status_code, 201, add.data)

    def test_student_can_join_a_different_course(self):
        EnrolledStudent.objects.create(email=self.email, student_set=self.first_set)
        other_subject = Subject.objects.create(
            name='Another Course', code='OTHER', instructor=self.other,
        )
        other_set = StudentSet.objects.create(
            name='Other Section', subject=other_subject, created_by=self.other,
        )
        self.client.force_authenticate(self.other)
        response = self.client.post(f'/api/instructor/subjects/{other_subject.pk}/students/', {
            'email': self.email, 'student_set_id': other_set.pk,
        }, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(EnrolledStudent.objects.filter(email=self.email).count(), 2)


class ExamListOrderingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.instructor = User.objects.create_user(username='order-instructor', is_staff=True)
        cls.student = User.objects.create_user(
            username='order-student', email='order-student@example.com',
        )
        cls.subject = Subject.objects.create(
            name='Order Science', code='ORDER', instructor=cls.instructor,
        )
        roster = StudentSet.objects.create(
            name='Section A', subject=cls.subject, created_by=cls.instructor,
        )
        EnrolledStudent.objects.create(email=cls.student.email, student_set=roster)
        cls.older = ExamSet.objects.create(
            subject=cls.subject, title='Older exam', is_final=True,
            due_at=timezone.now() + timedelta(days=30),
        )
        cls.newer = ExamSet.objects.create(
            subject=cls.subject, title='Newer exam', is_final=True,
            due_at=timezone.now() + timedelta(days=7),
        )

    def test_student_and_instructor_exam_lists_are_newest_first(self):
        client = APIClient()
        client.force_authenticate(self.student)
        response = client.get('/api/student/exams/')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            [row['id'] for row in response.data['exam_sets']],
            [self.newer.id, self.older.id],
        )

        client.force_authenticate(self.instructor)
        response = client.get(f'/api/instructor/subjects/{self.subject.id}/exam-sets/')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            [row['id'] for row in response.data['exam_sets']],
            [self.newer.id, self.older.id],
        )
        response = client.get(f'/api/instructor/subjects/{self.subject.id}/exam-progress/')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            [row['exam_set_id'] for row in response.data['progress']],
            [self.newer.id, self.older.id],
        )
        self.assertTrue(all(row['created_at'] for row in response.data['progress']))


@override_settings(SECRET_KEY='exam-question-order-test-key')
class ExamQuestionOrderTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.instructor = User.objects.create(username='instructor', is_staff=True)
        cls.subject = Subject.objects.create(
            name='Science', code='SCI', instructor=cls.instructor,
        )
        roster = StudentSet.objects.create(name='Section A', subject=cls.subject)
        cls.students = [
            User.objects.create(username=f'student{i}', email=f'student{i}@example.com')
            for i in range(2)
        ]
        for student in cls.students:
            EnrolledStudent.objects.create(email=student.email, student_set=roster)
        cls.exam = ExamSet.objects.create(
            subject=cls.subject, title='Exam', is_final=True, max_attempts=2,
        )
        cls.questions = [
            ExamQuestion.objects.create(
                exam_set=cls.exam, order=i + 1, question_text=f'Question {i}',
                question_type=ExamQuestion.TYPE_MULTIPLE_CHOICE,
                choices=[f'Correct {i}', f'Wrong {i}'], correct_answer=f'Correct {i}',
            )
            for i in range(12)
        ]

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.students[0])
        self.url = f'/api/student/exams/{self.exam.pk}/questions/'

    def fetch_questions(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200, response.data)
        return response.data['questions']

    def test_exam_list_exposes_terminated_status(self):
        submission = ExamSubmission.objects.create(
            exam_set=self.exam,
            student_email=self.students[0].email,
            is_done=True,
            terminated=True,
        )
        response = self.client.get('/api/student/exams/')
        self.assertEqual(response.status_code, 200, response.data)
        listed = next(row for row in response.data['exam_sets'] if row['id'] == self.exam.pk)
        self.assertTrue(listed['is_done'])
        self.assertTrue(listed['terminated'])
        submission.terminated = False
        submission.save(update_fields=['terminated'])
        response = self.client.get('/api/student/exams/')
        listed = next(row for row in response.data['exam_sets'] if row['id'] == self.exam.pk)
        self.assertFalse(listed['terminated'])

    def test_shuffle_is_complete_stable_and_specific_to_student(self):
        first = self.fetch_questions()
        ids = [q['id'] for q in first]
        original_ids = [q.pk for q in self.questions]
        self.assertCountEqual(ids, original_ids)
        self.assertNotEqual(ids, original_ids)
        self.assertEqual([q['order'] for q in first], list(range(1, 13)))
        self.assertEqual(first, self.fetch_questions())
        originals = {q.pk: q for q in self.questions}
        for question in first:
            self.assertNotIn('correct_answer', question)
            self.assertCountEqual(question['choices'], originals[question['id']].choices)
            self.assertEqual(question['question_text'], originals[question['id']].question_text)
        self.assertTrue(any(
            question['choices'] != originals[question['id']].choices
            for question in first
        ))
        self.client.force_authenticate(self.students[1])
        second = self.fetch_questions()
        second_ids = [q['id'] for q in second]
        self.assertCountEqual(second_ids, ids)
        self.assertNotEqual(second_ids, ids)
        second_choices = {q['id']: q['choices'] for q in second}
        self.assertTrue(any(
            question['choices'] != second_choices[question['id']]
            for question in first
        ))

    def test_new_attempt_reshuffles_and_answers_grade_by_question_id(self):
        first = self.fetch_questions()
        correct_answers = {q.pk: q.correct_answer for q in self.questions}
        # Deliberately miss one answer to catch accidental grading by position.
        wrong_id = first[0]['id']
        response = self.client.post(
            f'/api/student/exams/{self.exam.pk}/submit/',
            {'answers': [
                {'question_id': q['id'], 'answer_text': (
                    'incorrect' if q['id'] == wrong_id else next(
                        choice for choice in q['choices']
                        if choice == correct_answers[q['id']]
                    )
                )}
                for q in first
            ]},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['mc_correct'], 11)
        self.assertEqual(response.data['mc_total'], 12)
        self.assertEqual(response.data['mc_score'], 91.67)
        answers = StudentAnswer.objects.filter(exam_set=self.exam)
        self.assertEqual(answers.count(), 12)
        self.assertFalse(answers.get(question_id=wrong_id).is_correct)
        self.assertEqual(answers.filter(is_correct=True).count(), 11)
        second = self.fetch_questions()
        self.assertNotEqual([q['id'] for q in first], [q['id'] for q in second])
        self.assertCountEqual([q['id'] for q in first], [q['id'] for q in second])
        self.assertEqual(second, self.fetch_questions())
        second_choices = {q['id']: q['choices'] for q in second}
        self.assertTrue(any(
            q['choices'] != second_choices[q['id']]
            for q in first
        ))
        submission = ExamSubmission.objects.get(exam_set=self.exam)
        self.assertEqual(submission.attempt_count, 2)
        self.assertFalse(submission.is_done)

    def test_exam_list_exposes_attempts_until_limit_is_reached(self):
        list_url = '/api/student/exams/'
        exam_url = f'/api/student/exams/{self.exam.pk}/submit/'

        def listed_exam():
            response = self.client.get(list_url)
            self.assertEqual(response.status_code, 200, response.data)
            return next(row for row in response.data['exam_sets'] if row['id'] == self.exam.pk)

        self.assertEqual((listed_exam()['attempt_count'], listed_exam()['max_attempts']), (0, 2))
        for attempt in (1, 2):
            questions = self.fetch_questions()
            listed = listed_exam()
            self.assertEqual(listed['attempt_count'], attempt)
            self.assertFalse(listed['is_done'])
            response = self.client.post(
                exam_url,
                {'answers': [{'question_id': questions[0]['id'], 'answer_text': 'answer'}]},
                format='json',
            )
            self.assertEqual(response.status_code, 200, response.data)
            listed = listed_exam()
            self.assertTrue(listed['is_done'])
            self.assertEqual(listed['attempt_count'], attempt)
            self.assertEqual(listed['max_attempts'], 2)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403, response.data)

    def test_instructor_order_is_preserved(self):
        self.fetch_questions()
        self.client.force_authenticate(self.instructor)
        response = self.client.get(
            f'/api/instructor/subjects/{self.subject.pk}/exam-sets/{self.exam.pk}/questions/'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [(q['id'], q['order']) for q in response.data['questions']],
            [(q.pk, q.order) for q in self.questions],
        )

    def test_essay_questions_are_always_after_objective_questions(self):
        essays = [
            ExamQuestion.objects.create(
                exam_set=self.exam,
                order=20 + index,
                question_text=f'Essay {index}',
                question_type=ExamQuestion.TYPE_ESSAY,
            )
            for index in range(2)
        ]

        questions = self.fetch_questions()
        types = [question['question_type'] for question in questions]

        self.assertEqual(types[-2:], [ExamQuestion.TYPE_ESSAY, ExamQuestion.TYPE_ESSAY])
        self.assertNotIn(ExamQuestion.TYPE_ESSAY, types[:-2])
        self.assertCountEqual([question['id'] for question in questions[-2:]], [q.pk for q in essays])

    def test_empty_and_single_question_exams(self):
        self.exam.questions.exclude(pk=self.questions[0].pk).delete()
        questions = self.fetch_questions()
        self.assertEqual([q['id'] for q in questions], [self.questions[0].pk])
        self.assertEqual(questions[0]['order'], 1)
        self.exam.questions.all().delete()
        self.assertEqual(self.fetch_questions(), [])


class ExamProctoringRestrictionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.instructor = User.objects.create_user(
            username='restriction-instructor',
            is_staff=True,
        )
        cls.subject = Subject.objects.create(
            name='Writing',
            code='WRITE',
            instructor=cls.instructor,
        )
        cls.exam = ExamSet.objects.create(
            subject=cls.subject,
            title='Flexible assessment',
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.instructor)
        self.detail_url = (
            f'/api/instructor/subjects/{self.subject.pk}/exam-sets/{self.exam.pk}/'
        )
        self.questions_url = f'{self.detail_url}questions/'

    def test_essay_only_exam_can_disable_quiz_wide_restrictions(self):
        ExamQuestion.objects.create(
            exam_set=self.exam,
            order=1,
            question_type=ExamQuestion.TYPE_ESSAY,
            question_text='Explain your answer.',
        )
        response = self.client.patch(
            self.detail_url,
            {'proctoring_restrictions': {
                'gaze_above': False,
                'gaze_below': False,
                'gaze_left': False,
                'gaze_right': True,
                'gadgets': False,
            }},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.exam.refresh_from_db()
        self.assertFalse(self.exam.detect_gaze_above)
        self.assertFalse(self.exam.detect_gaze_below)
        self.assertFalse(self.exam.detect_gaze_left)
        self.assertTrue(self.exam.detect_gaze_right)
        self.assertFalse(self.exam.detect_gadgets)

    def test_non_essay_question_enables_and_locks_all_restrictions(self):
        ExamSet.objects.filter(pk=self.exam.pk).update(
            detect_gaze_above=False,
            detect_gaze_below=False,
            detect_gaze_left=False,
            detect_gaze_right=False,
            detect_gadgets=False,
        )
        create_response = self.client.post(
            self.questions_url,
            {
                'question_type': ExamQuestion.TYPE_IDENTIFICATION,
                'question_text': 'Identify the concept.',
                'correct_answer': 'Concept',
            },
            format='json',
        )
        self.assertEqual(create_response.status_code, 201, create_response.data)
        self.exam.refresh_from_db()
        self.assertTrue(all([
            self.exam.detect_gaze_above,
            self.exam.detect_gaze_below,
            self.exam.detect_gaze_left,
            self.exam.detect_gaze_right,
            self.exam.detect_gadgets,
        ]))

        disable_response = self.client.patch(
            self.detail_url,
            {'proctoring_restrictions': {'gaze_left': False}},
            format='json',
        )
        self.assertEqual(disable_response.status_code, 400, disable_response.data)
        self.assertIn('at least one essay question', disable_response.data['error'].lower())

    def test_mixed_exam_with_an_essay_can_customize_restrictions(self):
        ExamQuestion.objects.create(
            exam_set=self.exam,
            order=1,
            question_type=ExamQuestion.TYPE_MULTIPLE_CHOICE,
            question_text='Choose one.',
            choices=['A', 'B'],
            correct_answer='A',
        )
        ExamQuestion.objects.create(
            exam_set=self.exam,
            order=2,
            question_type=ExamQuestion.TYPE_ESSAY,
            question_text='Explain your choice.',
        )

        response = self.client.patch(
            self.detail_url,
            {'proctoring_restrictions': {'gaze_left': False, 'gadgets': False}},
            format='json',
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.exam.refresh_from_db()
        self.assertFalse(self.exam.detect_gaze_left)
        self.assertFalse(self.exam.detect_gadgets)


@override_settings(STORAGES={'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'}})
class ExamQuestionUploadTests(TestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(username='upload-instructor', is_staff=True)
        self.subject = Subject.objects.create(
            name='Writing Uploads', code='WUPLOAD', instructor=self.instructor,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.instructor)
        self.url = f'/api/instructor/subjects/{self.subject.pk}/exam-sets/'

    def upload(self, content, question_format):
        return self.client.post(self.url, {
            'title': 'Uploaded exam',
            'due_at': '2030-01-01T12:00:00Z',
            'question_file_format': question_format,
            'exam_file': SimpleUploadedFile('questions.txt', content.encode('utf-8'), content_type='text/plain'),
        }, format='multipart')

    def test_uploads_blank_line_separated_essay_questions(self):
        response = self.upload(
            'Explain the water cycle.\n\nCompare mitosis and meiosis.',
            'essay',
        )

        self.assertEqual(response.status_code, 201, response.data)
        exam = ExamSet.objects.get(pk=response.data['id'])
        self.assertEqual(exam.questions.count(), 0)
        self.assertFalse(exam.exam_file)
        self.assertEqual(response.data['bank_questions_added'], 2)
        self.assertEqual(
            list(QuestionBankItem.objects.filter(subject=self.subject).order_by('id').values_list('question_type', 'question_text')),
            [
                (ExamQuestion.TYPE_ESSAY, 'Explain the water cycle.'),
                (ExamQuestion.TYPE_ESSAY, 'Compare mitosis and meiosis.'),
            ],
        )
        self.assertTrue(response.data['requires_all_restrictions'])

    def test_invalid_aiken_upload_returns_an_error_instead_of_empty_exam(self):
        response = self.upload('Question without choices or answer', 'aiken')

        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn('Aiken', response.data['error'])
        self.assertFalse(ExamSet.objects.exists())


class InstructorSubjectiveGradingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.instructor = User.objects.create_user(username='grading-instructor', is_staff=True)
        cls.other_instructor = User.objects.create_user(username='other-instructor', is_staff=True)
        cls.subject = Subject.objects.create(
            name='Writing', code='WRITE', instructor=cls.instructor,
        )
        cls.roster = StudentSet.objects.create(
            name='Section A', subject=cls.subject, created_by=cls.instructor,
        )
        cls.student_email = 'writer@example.com'
        EnrolledStudent.objects.create(email=cls.student_email, student_set=cls.roster)
        cls.exam = ExamSet.objects.create(subject=cls.subject, title='Written Exam', is_final=True)
        cls.auto_question = ExamQuestion.objects.create(
            exam_set=cls.exam,
            order=1,
            question_type=ExamQuestion.TYPE_MULTIPLE_CHOICE,
            question_text='Pick A',
            choices=['A', 'B'],
            correct_answer='A',
        )
        cls.essay_question = ExamQuestion.objects.create(
            exam_set=cls.exam,
            order=2,
            question_type=ExamQuestion.TYPE_ESSAY,
            question_text='Explain your answer.',
            points=5,
        )
        cls.submission = ExamSubmission.objects.create(
            exam_set=cls.exam,
            student_email=cls.student_email,
            is_done=True,
            score=100,
        )
        StudentAnswer.objects.create(
            exam_set=cls.exam,
            question=cls.auto_question,
            student_email=cls.student_email,
            answer_text='A',
            is_correct=True,
        )
        cls.essay_answer = StudentAnswer.objects.create(
            exam_set=cls.exam,
            question=cls.essay_question,
            student_email=cls.student_email,
            answer_text='A thoughtful long-form response.',
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.instructor)
        self.url = (
            f'/api/instructor/subjects/{self.subject.pk}/exam-sets/'
            f'{self.exam.pk}/integrity-report/?student_email={self.student_email}'
        )

    def test_instructor_can_view_and_score_subjective_answer(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(response.data['manual_grading_complete'])
        self.assertEqual(response.data['subjective_answers'], [{
            'answer_id': self.essay_answer.pk,
            'question_id': self.essay_question.pk,
            'order': 2,
            'question_text': 'Explain your answer.',
            'answer_text': 'A thoughtful long-form response.',
            'max_points': 5.0,
            'awarded_points': None,
        }])

        response = self.client.patch(
            self.url,
            {'grades': [{'answer_id': self.essay_answer.pk, 'awarded_points': 4}]},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data['manual_grading_complete'])
        self.assertEqual(response.data['subjective_answers'][0]['awarded_points'], 4.0)
        self.assertEqual(response.data['submission']['score'], 83.33)
        self.essay_answer.refresh_from_db()
        self.submission.refresh_from_db()
        self.assertEqual(self.essay_answer.awarded_points, 4)
        self.assertEqual(self.submission.score, Decimal('83.33'))

    def test_grade_must_be_within_question_points(self):
        response = self.client.patch(
            self.url,
            {'grades': [{'answer_id': self.essay_answer.pk, 'awarded_points': 6}]},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('between 0 and 5', response.data['error'])
        self.essay_answer.refresh_from_db()
        self.assertIsNone(self.essay_answer.awarded_points)

    def test_other_instructor_cannot_review_submission(self):
        self.client.force_authenticate(self.other_instructor)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

    def test_progress_marks_subjective_answer_as_pending(self):
        response = self.client.get(
            f'/api/instructor/subjects/{self.subject.pk}/exam-progress/'
        )
        self.assertEqual(response.status_code, 200, response.data)
        row = response.data['progress'][0]
        self.assertEqual(row['subjective_count'], 1)
        self.assertEqual(row['pending_subjective_count'], 1)
        self.assertFalse(row['manual_grading_complete'])


class _Q:
    def __init__(self, question_type, correct_answer='', case_sensitive=False):
        self.question_type = question_type
        self.correct_answer = correct_answer
        self.case_sensitive = case_sensitive


class GradingTests(SimpleTestCase):
    def test_identification_case_insensitive_and_whitespace(self):
        q = _Q('identification', 'Photosynthesis')
        ok, credit = grade_question(q, '  photosynthesis. ')
        self.assertTrue(ok)
        self.assertEqual(credit, 1.0)

    def test_identification_alternatives(self):
        q = _Q('identification', 'HTTP | Hypertext Transfer Protocol')
        ok, _ = grade_question(q, 'http')
        self.assertTrue(ok)
        ok, _ = grade_question(q, 'Hypertext Transfer Protocol')
        self.assertTrue(ok)

    def test_identification_wrong_answer(self):
        q = _Q('identification', 'Manila')
        ok, credit = grade_question(q, 'Cebu')
        self.assertFalse(ok)
        self.assertEqual(credit, 0.0)

    def test_identification_manual_when_no_key(self):
        q = _Q('identification', '')
        ok, credit = grade_question(q, 'anything')
        self.assertIsNone(ok)
        self.assertEqual(credit, 0.0)

    def test_enumeration_newline_and_numbered(self):
        q = _Q('enumeration', 'Apple\nBanana\nOrange')
        ok, credit = grade_question(q, '1. apple\n2. banana\n3. orange')
        self.assertTrue(ok)
        self.assertEqual(credit, 1.0)

    def test_enumeration_comma_separated(self):
        q = _Q('enumeration', 'Apple\nBanana')
        ok, credit = grade_question(q, 'banana, apple')
        self.assertTrue(ok)
        self.assertEqual(credit, 1.0)

    def test_enumeration_partial_credit(self):
        q = _Q('enumeration', 'Apple\nBanana\nOrange')
        ok, credit = grade_question(q, 'apple\nbanana')
        self.assertFalse(ok)
        self.assertAlmostEqual(credit, 2 / 3)

    def test_multiple_choice(self):
        q = _Q('multiple_choice', 'Option A')
        ok, credit = grade_question(q, 'option a')
        self.assertTrue(ok)
        self.assertEqual(credit, 1.0)


class GazeLabelStickyTests(SimpleTestCase):
    CLASSES = [
        "Looking above the screen",
        "Looking at the left",
        "Looking at the right",
        "Looking at the screen (Normal)",
        "Looking below",
    ]

    def test_residual_right_does_not_stick_when_looking_at_screen(self):
        import numpy as np
        from gaze_tracker.inference import pick_gaze_label

        geo = np.zeros(14, dtype=np.float32)
        probs = np.array([0.04, 0.05, 0.41, 0.46, 0.04], dtype=np.float32)
        idx, _ = pick_gaze_label(probs, geo, self.CLASSES)
        self.assertEqual(self.CLASSES[idx], "Looking at the screen (Normal)")

    def test_clear_right_look_still_detected(self):
        import numpy as np
        from gaze_tracker.inference import pick_gaze_label

        geo = np.zeros(14, dtype=np.float32)
        geo[11] = 0.18
        geo[5] = 0.12
        geo[7] = 0.12
        probs = np.array([0.05, 0.08, 0.62, 0.18, 0.07], dtype=np.float32)
        idx, _ = pick_gaze_label(probs, geo, self.CLASSES)
        self.assertEqual(self.CLASSES[idx], "Looking at the right")

    def test_held_left_look_not_forced_to_normal(self):
        import numpy as np
        from gaze_tracker.inference import pick_gaze_label

        geo = np.zeros(14, dtype=np.float32)
        geo[11] = -0.08
        geo[5] = -0.09
        geo[7] = -0.09
        probs = np.array([0.06, 0.45, 0.10, 0.30, 0.09], dtype=np.float32)
        idx, _ = pick_gaze_label(probs, geo, self.CLASSES)
        self.assertEqual(self.CLASSES[idx], "Looking at the left")

    def test_held_above_look_detected(self):
        import numpy as np
        from gaze_tracker.inference import pick_gaze_label

        geo = np.zeros(14, dtype=np.float32)
        geo[1] = -0.06
        geo[6] = -0.05
        geo[8] = -0.05
        geo[12] = -0.06
        probs = np.array([0.40, 0.08, 0.07, 0.35, 0.10], dtype=np.float32)
        idx, _ = pick_gaze_label(probs, geo, self.CLASSES)
        self.assertEqual(self.CLASSES[idx], "Looking above the screen")

    def test_clear_left_look_detected(self):
        import numpy as np
        from gaze_tracker.inference import pick_gaze_label

        geo = np.zeros(14, dtype=np.float32)
        geo[11] = -0.18
        geo[5] = -0.12
        geo[7] = -0.12
        probs = np.array([0.05, 0.62, 0.08, 0.18, 0.07], dtype=np.float32)
        idx, _ = pick_gaze_label(probs, geo, self.CLASSES)
        self.assertEqual(self.CLASSES[idx], "Looking at the left")

    def test_small_horizontal_jitter_stays_normal(self):
        import numpy as np
        from gaze_tracker.inference import pick_gaze_label

        geo = np.zeros(14, dtype=np.float32)
        geo[11] = -0.04
        geo[5] = -0.04
        geo[7] = -0.04
        probs = np.array([0.04, 0.52, 0.05, 0.35, 0.04], dtype=np.float32)
        idx, _ = pick_gaze_label(probs, geo, self.CLASSES)
        self.assertEqual(self.CLASSES[idx], "Looking at the screen (Normal)")

    def test_clear_left_geometry_recovers_from_opposite_model_label(self):
        import numpy as np
        from gaze_tracker.inference import pick_gaze_label

        geo = np.zeros(14, dtype=np.float32)
        geo[11] = -0.11
        geo[5] = -0.12
        geo[7] = -0.12
        probs = np.array([0.04, 0.05, 0.55, 0.30, 0.06], dtype=np.float32)
        idx, confidence = pick_gaze_label(probs, geo, self.CLASSES)
        self.assertEqual(self.CLASSES[idx], "Looking at the left")
        self.assertGreaterEqual(confidence, 0.50)


@override_settings(STORAGES={'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'}})
class ExamSetDeletionPurgesStudentRecordsTests(TestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(
            username='purge-instructor', is_staff=True,
        )
        self.subject = Subject.objects.create(
            name='Purge Course', code='PRG', instructor=self.instructor,
        )
        self.roster = StudentSet.objects.create(
            name='Section A', subject=self.subject, created_by=self.instructor,
        )
        EnrolledStudent.objects.create(
            email='student@example.com', student_set=self.roster,
        )
        self.exam = ExamSet.objects.create(
            subject=self.subject, title='Quiz to delete', is_final=True,
        )
        self.question = ExamQuestion.objects.create(
            exam_set=self.exam,
            order=1,
            question_type=ExamQuestion.TYPE_MULTIPLE_CHOICE,
            question_text='Choose.',
            choices=['A', 'B'],
            correct_answer='A',
        )
        self.submission = ExamSubmission.objects.create(
            exam_set=self.exam,
            student_email='student@example.com',
            is_done=True,
            score=Decimal('100.00'),
            integrity_score=Decimal('85.00'),
        )
        StudentAnswer.objects.create(
            exam_set=self.exam,
            question=self.question,
            student_email='student@example.com',
            answer_text='A',
        )
        from accounts.models import ExamIntegrityReport, ExamProctoringEvent
        ExamProctoringEvent.objects.create(
            submission=self.submission,
            attempt_number=1,
            event_type=ExamProctoringEvent.EVENT_GADGET_DETECTED,
            severity=ExamProctoringEvent.SEVERITY_WARNING,
            message='phone',
        )
        ExamIntegrityReport.objects.create(
            submission=self.submission,
            attempt_number=1,
            integrity_score=Decimal('85.00'),
        )
        self.client = APIClient()
        self.client.force_authenticate(self.instructor)

    def test_deleting_exam_removes_progress_and_student_records(self):
        from accounts.models import ExamIntegrityReport, ExamProctoringEvent

        progress_before = self.client.get(
            f'/api/instructor/subjects/{self.subject.pk}/exam-progress/',
        )
        self.assertEqual(progress_before.status_code, 200, progress_before.data)
        self.assertTrue(
            any(row['exam_set_id'] == self.exam.pk for row in progress_before.data['progress']),
        )

        delete_response = self.client.delete(
            f'/api/instructor/subjects/{self.subject.pk}/exam-sets/{self.exam.pk}/',
        )
        self.assertEqual(delete_response.status_code, 204)

        self.assertFalse(ExamSet.objects.filter(pk=self.exam.pk).exists())
        self.assertFalse(ExamSubmission.objects.filter(exam_set_id=self.exam.pk).exists())
        self.assertFalse(StudentAnswer.objects.filter(exam_set_id=self.exam.pk).exists())
        self.assertFalse(ExamProctoringEvent.objects.filter(submission_id=self.submission.pk).exists())
        self.assertFalse(ExamIntegrityReport.objects.filter(submission_id=self.submission.pk).exists())

        progress_after = self.client.get(
            f'/api/instructor/subjects/{self.subject.pk}/exam-progress/',
        )
        self.assertEqual(progress_after.status_code, 200, progress_after.data)
        self.assertFalse(
            any(row['exam_set_id'] == self.exam.pk for row in progress_after.data['progress']),
        )

