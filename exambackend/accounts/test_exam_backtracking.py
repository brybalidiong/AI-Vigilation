from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import EnrolledStudent, ExamQuestion, ExamSet, ExamSubmission, StudentAnswer, StudentSet, Subject, UserProfile


class ExamBacktrackingTests(TestCase):
    def setUp(self):
        instructor = User.objects.create_user('instructor', email='instructor@example.com', is_staff=True)
        self.student = User.objects.create_user('student', email='student@example.com')
        UserProfile.objects.create(user=self.student, role='student', is_enrolled=True)
        subject = Subject.objects.create(instructor=instructor, name='Synthetic course', code='SYN')
        roster = StudentSet.objects.create(subject=subject, created_by=instructor, name='Section A')
        EnrolledStudent.objects.create(student_set=roster, email=self.student.email)
        self.exam = ExamSet.objects.create(subject=subject, title='One-way exam', is_final=True, allow_backtracking=False)
        for number in range(3):
            ExamQuestion.objects.create(
                exam_set=self.exam, order=number, question_type='identification',
                question_text=f'Question {number}', correct_answer=f'answer {number}',
            )
        self.client = APIClient()
        self.client.force_authenticate(self.student)

    def test_advance_locks_answer_and_refresh_resumes(self):
        url = f'/api/student/exams/{self.exam.id}/questions/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['allow_backtracking'])
        first_id = response.data['questions'][0]['id']
        second_id = response.data['questions'][1]['id']
        advance_url = f'/api/student/exams/{self.exam.id}/advance/'
        response = self.client.post(advance_url, {'question_id': first_id, 'answer_text': 'original'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['question_index'], 1)
        self.assertEqual(self.client.post(advance_url, {'question_id': first_id, 'answer_text': 'changed'}, format='json').status_code, 409)
        refreshed = self.client.get(url)
        self.assertEqual(refreshed.data['question_index'], 1)
        self.assertEqual(refreshed.data['locked_answers'][str(first_id)], 'original')
        answers = [{'question_id': question['id'], 'answer_text': 'changed'} for question in refreshed.data['questions']]
        answers[1]['answer_text'] = 'current'
        submitted = self.client.post(f'/api/student/exams/{self.exam.id}/submit/', {'answers': answers}, format='json')
        self.assertEqual(submitted.status_code, 200)
        self.assertEqual(StudentAnswer.objects.get(exam_set=self.exam, question_id=first_id).answer_text, 'original')
        self.assertEqual(StudentAnswer.objects.get(exam_set=self.exam, question_id=second_id).answer_text, 'current')
        self.assertEqual(ExamSubmission.objects.get(exam_set=self.exam).question_index, 1)
