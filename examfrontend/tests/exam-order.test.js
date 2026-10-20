import assert from 'node:assert/strict';
import test from 'node:test';

import { canRetakeExam, compareExamsNewestFirst, studentExamOnDashboard } from '../src/utils/examTimeline.js';

test('exam lists use creation order even when deadlines and titles disagree', () => {
  const exams = [
    { id: 1, title: 'A', created_at: '2026-01-01T10:00:00Z', due_at: '2026-12-01T10:00:00Z' },
    { id: 3, title: 'Z', created_at: '2026-03-01T10:00:00Z', due_at: '2026-04-01T10:00:00Z' },
    { id: 2, title: 'B', created_at: '2026-02-01T10:00:00Z', due_at: '2026-05-01T10:00:00Z' },
  ];
  assert.deepEqual(exams.sort(compareExamsNewestFirst).map(exam => exam.id), [3, 2, 1]);
});

test('equal creation times use newest ID first', () => {
  const exams = [
    { exam_set_id: 4, created_at: '2026-03-01T10:00:00Z' },
    { exam_set_id: 5, created_at: '2026-03-01T10:00:00Z' },
  ];
  assert.deepEqual(exams.sort(compareExamsNewestFirst).map(exam => exam.exam_set_id), [5, 4]);
});

test('a submitted exam remains available for a second attempt until its limit or deadline', () => {
  const now = Date.parse('2026-10-21T01:00:00Z');
  const exam = {
    is_final: true,
    is_done: true,
    attempt_count: 1,
    max_attempts: 2,
    available_from: '2026-10-20T01:00:00Z',
    due_at: '2026-10-22T01:00:00Z',
  };
  assert.equal(canRetakeExam(exam, now), true);
  assert.equal(studentExamOnDashboard(exam, { now, withinDays: 3650 }), true);
  assert.equal(canRetakeExam({ ...exam, attempt_count: 2 }, now), false);
  assert.equal(canRetakeExam(exam, Date.parse('2026-10-23T01:00:00Z')), false);
  assert.equal(studentExamOnDashboard({ ...exam, attempt_count: 2 }, { now, withinDays: 3650 }), false);
});
