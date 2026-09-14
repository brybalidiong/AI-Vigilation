from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from openpyxl import Workbook
from rest_framework.test import APIClient
from decimal import Decimal
from io import BytesIO

from accounts.grading import grade_question
from accounts.models import (
    EnrolledStudent, ExamQuestion, ExamSet, ExamSubmission, StudentAnswer,
    StudentSet, Subject, UserProfile,
)


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
            self.assertEqual(question['choices'], originals[question['id']].choices)
            self.assertEqual(question['question_text'], originals[question['id']].question_text)
        self.client.force_authenticate(self.students[1])
        second_ids = [q['id'] for q in self.fetch_questions()]
        self.assertCountEqual(second_ids, ids)
        self.assertNotEqual(second_ids, ids)

    def test_new_attempt_reshuffles_and_answers_grade_by_question_id(self):
        first = self.fetch_questions()
        correct_answers = {q.pk: q.correct_answer for q in self.questions}
        # Deliberately miss one answer to catch accidental grading by position.
        wrong_id = first[0]['id']
        response = self.client.post(
            f'/api/student/exams/{self.exam.pk}/submit/',
            {'answers': [
                {'question_id': q['id'], 'answer_text': (
                    'incorrect' if q['id'] == wrong_id else correct_answers[q['id']]
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
        submission = ExamSubmission.objects.get(exam_set=self.exam)
        self.assertEqual(submission.attempt_count, 2)
        self.assertFalse(submission.is_done)

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

    def test_empty_and_single_question_exams(self):
        self.exam.questions.exclude(pk=self.questions[0].pk).delete()
        questions = self.fetch_questions()
        self.assertEqual([q['id'] for q in questions], [self.questions[0].pk])
        self.assertEqual(questions[0]['order'], 1)
        self.exam.questions.all().delete()
        self.assertEqual(self.fetch_questions(), [])


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

