import { examTimelineDisplayAt, parseExamDate } from './examTimeline.js';

export function calendarDayKey(date) {
  const value = date instanceof Date ? date : parseExamDate(date);
  if (!value) return '';
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, '0');
  const day = String(value.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export function calendarMonthDays(monthDate, exams = []) {
  const year = monthDate.getFullYear();
  const month = monthDate.getMonth();
  const countByDay = new Map();
  for (const exam of exams) {
    const key = calendarDayKey(examTimelineDisplayAt(exam));
    if (key) countByDay.set(key, (countByDay.get(key) || 0) + 1);
  }
  const leadingBlanks = (new Date(year, month, 1).getDay() + 6) % 7;
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  return [
    ...Array.from({ length: leadingBlanks }, (_, index) => ({ key: `blank-${index}`, blank: true })),
    ...Array.from({ length: daysInMonth }, (_, index) => {
      const date = new Date(year, month, index + 1);
      const key = calendarDayKey(date);
      return { key, date, day: index + 1, count: countByDay.get(key) || 0 };
    }),
  ];
}
