import test from 'node:test';
import assert from 'node:assert/strict';
import { calendarDayKey, calendarMonthDays } from '../src/utils/examCalendar.js';

test('calendar aligns Monday first and counts exams on their displayed local day', () => {
  const month = new Date(2026, 9, 1);
  const due = new Date(2026, 9, 21, 14, 30).toISOString();
  const exams = [
    { due_at: due },
    { due_at: due },
  ];
  const days = calendarMonthDays(month, exams);
  assert.equal(days.filter((day) => day.blank).length, 3);
  assert.equal(days.find((day) => day.key === '2026-10-21').count, 2);
  assert.equal(calendarDayKey(new Date(2026, 9, 31)), '2026-10-31');
});
