from django.contrib.auth.models import User
from django.apps import apps
from django.test import TestCase
from rest_framework.test import APIClient
from importlib import import_module

from accounts.models import ExamQuestion, ExamSet, QuestionBankBatch, QuestionBankItem, Subject


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
