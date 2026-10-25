from django.contrib.auth.models import User
from django.apps import apps
from django.test import TestCase
from rest_framework.test import APIClient
from importlib import import_module

from accounts.models import EnrolledStudent, ExamQuestion, ExamSet, ExamSubmission, QuestionBankBatch, QuestionBankItem, StudentAnswer, StudentSet, Subject


class CourseQuestionBankTests(TestCase):
    def setUp(self):
        self.instructor = User.objects.create_user('bank-instructor', is_staff=True)
        self.other_instructor = User.objects.create_user('other-instructor', is_staff=True)
        self.subject = Subject.objects.create(instructor=self.instructor, code='BANK', name='Synthetic course')
        self.other_subject = Subject.objects.create(instructor=self.other_instructor, code='OTHER', name='Other course')
        self.exam = ExamSet.objects.create(subject=self.subject, title='Draft exam')
        self.client = APIClient()
        self.client.force_authenticate(self.instructor)
        self.bank_url = f'/api/instructor/subjects/{self.subject.id}/question-bank/'
        self.add_url = f'/api/instructor/subjects/{self.subject.id}/exam-sets/{self.exam.id}/questions/from-bank/'

    def test_bank_selection_copies_questions_and_deletion_preserves_exam(self):
        response = self.client.post(self.bank_url, {
            'question_type': 'multiple_choice', 'question_text': 'Synthetic prompt?',
            'choices': ['One', 'Two'], 'correct_answer': 'Two',
        }, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        bank_id = response.data['id']
        self.assertEqual(self.exam.questions.count(), 0)
        selected = self.client.post(self.add_url, {'question_ids': [bank_id]}, format='json')
        self.assertEqual(selected.status_code, 201, selected.data)
        self.assertEqual(selected.data['added_count'], 1)
        self.assertEqual(self.client.post(self.add_url, {'question_ids': [bank_id]}, format='json').data['added_count'], 0)
        question = ExamQuestion.objects.get(exam_set=self.exam)
        self.assertEqual(question.correct_answer, 'Two')
        deleted = self.client.delete(f'{self.bank_url}{bank_id}/')
        self.assertEqual(deleted.status_code, 204)
        question.refresh_from_db()
        self.assertIsNone(question.bank_item_id)
        self.assertEqual(question.question_text, 'Synthetic prompt?')

    def test_cannot_use_other_courses_questions_or_modify_published_exam(self):
        foreign = QuestionBankItem.objects.create(subject=self.other_subject, question_type='essay', question_text='Foreign prompt')
        self.assertEqual(self.client.post(self.add_url, {'question_ids': [foreign.id]}, format='json').status_code, 400)
        self.assertEqual(self.client.get(f'/api/instructor/subjects/{self.other_subject.id}/question-bank/').status_code, 404)
        own = QuestionBankItem.objects.create(subject=self.subject, question_type='essay', question_text='Own prompt')
        self.exam.is_final = True
        self.exam.save(update_fields=['is_final'])
        self.assertEqual(self.client.post(self.add_url, {'question_ids': [own.id]}, format='json').status_code, 403)

    def test_bulk_import_populates_bank_only(self):
        response = self.client.post(self.bank_url, {
            'bulk_text': 'What is two plus two?\nA. Three\nB. Four\nANSWER: B',
            'question_file_format': 'aiken',
            'batch_name': 'Chapter one',
        }, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['created_count'], 1)
        self.assertEqual(QuestionBankItem.objects.get(subject=self.subject).correct_answer, 'Four')
        self.assertEqual(QuestionBankBatch.objects.get(subject=self.subject).name, 'Chapter one')
        self.assertEqual(self.exam.questions.count(), 0)

    def test_essay_points_and_word_limit_copy_from_bank_to_exam(self):
        response = self.client.post(self.bank_url, {
            'question_type': 'essay', 'question_text': 'Explain the design.',
            'points': 8, 'max_words': 120,
        }, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual((response.data['points'], response.data['max_words']), (8, 120))
        selected = self.client.post(self.add_url, {'question_ids': [response.data['id']]}, format='json')
        self.assertEqual(selected.status_code, 201, selected.data)
        question = self.exam.questions.get()
        self.assertEqual((question.points, question.max_words), (8, 120))

    def test_essay_import_applies_points_and_word_limit_to_each_prompt(self):
        response = self.client.post(self.bank_url, {
            'bulk_text': 'Explain concept A.\n\nExplain concept B.',
            'question_file_format': 'essay', 'batch_name': 'Writing',
            'points': 10, 'max_words': 250,
        }, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['created_count'], 2)
        self.assertEqual(set(QuestionBankItem.objects.filter(subject=self.subject).values_list('points', 'max_words')), {(10, 250)})

    def test_invalid_essay_limit_creates_no_batch_or_question(self):
        response = self.client.post(self.bank_url, {
            'bulk_text': 'Explain concept A.', 'question_file_format': 'essay',
            'batch_name': 'Writing', 'points': 10, 'max_words': 10001,
        }, format='json')
        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(QuestionBankBatch.objects.filter(subject=self.subject).exists())

    def test_new_batch_choice_keeps_same_named_batches_separate(self):
        existing = QuestionBankBatch.objects.create(subject=self.subject, name='Unit one')
        response = self.client.post(self.bank_url, {
            'question_type': 'essay', 'question_text': 'Synthetic new prompt',
            'batch_name': 'Unit one', 'create_new_batch': True,
        }, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertNotEqual(response.data['batch_id'], existing.id)
        self.assertEqual(QuestionBankBatch.objects.filter(subject=self.subject, name='Unit one').count(), 2)

    def test_manual_and_bulk_questions_append_to_selected_batch(self):
        batch = QuestionBankBatch.objects.create(subject=self.subject, name='Unit one')
        manual = self.client.post(self.bank_url, {
            'question_type': 'essay', 'question_text': 'Synthetic manual prompt',
            'batch_id': batch.id,
        }, format='json')
        self.assertEqual(manual.status_code, 201, manual.data)
        self.assertEqual(manual.data['batch_id'], batch.id)
        imported = self.client.post(self.bank_url, {
            'bulk_text': 'What is two plus two?\nA. Three\nB. Four\nANSWER: B',
            'question_file_format': 'aiken', 'batch_id': batch.id,
        }, format='json')
        self.assertEqual(imported.status_code, 201, imported.data)
        self.assertEqual(imported.data['batch']['id'], batch.id)
        self.assertEqual(imported.data['created_count'], 1)
        self.assertEqual(batch.questions.count(), 2)
        self.assertEqual(QuestionBankBatch.objects.filter(subject=self.subject).count(), 1)

    def test_cannot_append_to_another_courses_batch(self):
        foreign = QuestionBankBatch.objects.create(subject=self.other_subject, name='Private batch')
        manual = self.client.post(self.bank_url, {
            'question_type': 'essay', 'question_text': 'Synthetic manual prompt',
            'batch_id': foreign.id,
        }, format='json')
        self.assertEqual(manual.status_code, 400, manual.data)
        imported = self.client.post(self.bank_url, {
            'bulk_text': 'What is two plus two?\nA. Three\nB. Four\nANSWER: B',
            'question_file_format': 'aiken', 'batch_id': foreign.id,
        }, format='json')
        self.assertEqual(imported.status_code, 400, imported.data)
        self.assertEqual(QuestionBankItem.objects.count(), 0)

    def test_batches_group_questions_and_can_be_deleted_without_changing_exam(self):
        first = self.client.post(self.bank_url, {
            'question_type': 'essay', 'question_text': 'Explain concept A', 'batch_name': 'Unit one',
        }, format='json')
        second = self.client.post(self.bank_url, {
            'question_type': 'essay', 'question_text': 'Explain concept B', 'batch_name': 'Unit one',
        }, format='json')
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(second.status_code, 201, second.data)
        response = self.client.get(self.bank_url)
        self.assertEqual(len(response.data['batches']), 1)
        batch = response.data['batches'][0]
        self.assertEqual(batch['name'], 'Unit one')
        self.assertEqual(len(batch['questions']), 2)
        self.assertEqual(self.client.post(self.add_url, {'question_ids': [first.data['id']]}, format='json').status_code, 201)
        self.assertEqual(self.client.delete(f'{self.bank_url}batches/{batch["id"]}/').status_code, 204)
        self.assertEqual(QuestionBankItem.objects.filter(subject=self.subject).count(), 0)
        self.assertEqual(self.exam.questions.count(), 1)
        self.assertEqual(self.exam.questions.get().question_text, 'Explain concept A')

    def test_cannot_delete_another_courses_batch(self):
        foreign = QuestionBankBatch.objects.create(subject=self.other_subject, name='Private batch')
        self.assertEqual(self.client.delete(f'{self.bank_url}batches/{foreign.id}/').status_code, 404)

    def test_batch_migration_groups_existing_bank_items_by_exam(self):
        item = QuestionBankItem.objects.create(subject=self.subject, question_type='essay', question_text='Older prompt')
        ExamQuestion.objects.create(exam_set=self.exam, bank_item=item, question_type='essay', question_text='Older prompt')
        import_module('accounts.migrations.0044_question_bank_batches').group_existing_questions(apps, None)
        item.refresh_from_db()
        self.assertEqual(item.batch.name, self.exam.title)


class StudentEssayWordLimitTests(TestCase):
    def setUp(self):
        instructor = User.objects.create_user('essay-instructor', is_staff=True)
        self.student = User.objects.create_user('essay-student', email='essay-student@example.com')
        subject = Subject.objects.create(instructor=instructor, code='ESSAY', name='Essay course')
        student_set = StudentSet.objects.create(name='Section A', subject=subject, created_by=instructor)
        EnrolledStudent.objects.create(email=self.student.email, student_set=student_set)
        self.exam = ExamSet.objects.create(subject=subject, title='Essay exam', is_final=True)
        self.question = ExamQuestion.objects.create(
            exam_set=self.exam, question_type=ExamQuestion.TYPE_ESSAY,
            question_text='Explain the result.', points=5, max_words=2,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.student)
        self.questions_url = f'/api/student/exams/{self.exam.id}/questions/'
        self.submit_url = f'/api/student/exams/{self.exam.id}/submit/'

    def test_student_sees_limit_and_overlong_submission_is_rejected(self):
        questions = self.client.get(self.questions_url)
        self.assertEqual(questions.status_code, 200, questions.data)
        self.assertEqual((questions.data['questions'][0]['points'], questions.data['questions'][0]['max_words']), (5, 2))
        answer = {'question_id': self.question.id, 'answer_text': 'one two three'}
        rejected = self.client.post(self.submit_url, {'answers': [answer]}, format='json')
        self.assertEqual(rejected.status_code, 400, rejected.data)
        self.assertFalse(StudentAnswer.objects.filter(question=self.question).exists())
        self.assertFalse(ExamSubmission.objects.get(exam_set=self.exam).is_done)
        answer['answer_text'] = 'one two'
        accepted = self.client.post(self.submit_url, {'answers': [answer]}, format='json')
        self.assertEqual(accepted.status_code, 200, accepted.data)
        self.assertEqual(StudentAnswer.objects.get(question=self.question).answer_text, 'one two')

    def test_one_way_navigation_rejects_overlong_essay(self):
        self.exam.allow_backtracking = False
        self.exam.save(update_fields=['allow_backtracking'])
        ExamQuestion.objects.create(
            exam_set=self.exam, question_type=ExamQuestion.TYPE_ESSAY,
            question_text='Explain another result.', points=5, max_words=2,
        )
        questions = self.client.get(self.questions_url)
        self.assertEqual(questions.status_code, 200, questions.data)
        first_id = questions.data['questions'][0]['id']
        advance_url = f'/api/student/exams/{self.exam.id}/advance/'
        rejected = self.client.post(advance_url, {
            'question_id': first_id, 'answer_text': 'one two three',
        }, format='json')
        self.assertEqual(rejected.status_code, 400, rejected.data)
        submission = ExamSubmission.objects.get(exam_set=self.exam)
        self.assertEqual(submission.question_index, 0)
        accepted = self.client.post(advance_url, {
            'question_id': first_id, 'answer_text': 'one two',
        }, format='json')
        self.assertEqual(accepted.status_code, 200, accepted.data)
        submission.refresh_from_db()
        self.assertEqual(submission.question_index, 1)
