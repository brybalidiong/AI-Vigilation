import assert from 'node:assert/strict';
import test from 'node:test';

import { compareExamsNewestFirst } from '../src/utils/examTimeline.js';

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
