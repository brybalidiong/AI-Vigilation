/** Parse API / datetime-local values into a timestamp (local browser time). */
export function parseExamDate(raw) {
  if (!raw) return null;
  const d = new Date(raw);
  const t = d.getTime();
  return Number.isFinite(t) ? d : null;
}

/**
 * Which instant to show on the dashboard timeline (local calendar day + time).
 * - Not yet open → available_from
 * - Otherwise → due_at (deadline)
 */
export function examTimelineDisplayAt(exam) {
  if (!exam) return null;
  const now = Date.now();
  const start = parseExamDate(exam.available_from);
  const due = parseExamDate(exam.due_at);

  if (start && start.getTime() > now) {
    return exam.available_from;
  }
  if (due) {
    return exam.due_at;
  }
  if (start) {
    return exam.available_from;
  }
  return exam.created_at || null;
}

/** Timestamp used for sorting and timeline window checks. */
export function examAnchorTimestamp(exam) {
  const d = parseExamDate(examTimelineDisplayAt(exam));
  return d ? d.getTime() : 0;
}

/** Most recently created exam first; ID breaks equal or missing timestamps. */
export function compareExamsNewestFirst(a, b) {
  const created = (exam) => parseExamDate(exam?.created_at)?.getTime() ?? 0;
  const difference = created(b) - created(a);
  if (difference) return difference;
  return Number(b?.id ?? b?.exam_set_id ?? 0) - Number(a?.id ?? a?.exam_set_id ?? 0);
}

export function formatTimelineDayHeader(rawOrDate) {
  const d = rawOrDate instanceof Date ? rawOrDate : parseExamDate(rawOrDate);
  if (!d) return 'Unknown date';
  return d
    .toLocaleDateString('en-GB', {
      weekday: 'long',
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    })
    .toUpperCase();
}

export function formatExamTimelineTime(exam) {
  const d = parseExamDate(examTimelineDisplayAt(exam));
  if (!d) return '';
  return d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
}

/** Month + day parts for the agenda date block (e.g. OCT / 05). */
export function formatExamTimelineDateParts(exam) {
  const d = parseExamDate(examTimelineDisplayAt(exam));
  if (!d) return { month: '—', day: '—' };
  return {
    month: d.toLocaleString('en-US', { month: 'short' }).toUpperCase(),
    day: String(d.getDate()).padStart(2, '0'),
  };
}

/**
 * Dashboard timeline: open now or opens / ends in the future.
 * Hides exams whose due date has already passed.
 */
export function isExamActiveOrUpcoming(exam, now = Date.now()) {
  const start = parseExamDate(exam?.available_from);
  const due = parseExamDate(exam?.due_at);

  if (start && start.getTime() > now) return true;
  if (!due) {
    return !start || start.getTime() <= now;
  }
  return due.getTime() >= now;
}

/** Within forward-looking window; never includes past-due exams. */
export function passesTimelineWindow(exam, now, withinDays) {
  if (!isExamActiveOrUpcoming(exam, now)) return false;

  const days = Number(withinDays);
  if (!days || days <= 0 || days >= 3650) return true;

  const withinMs = days * 24 * 60 * 60 * 1000;
  const anchor = examAnchorTimestamp(exam);
  if (!anchor) return false;

  return anchor >= now && anchor <= now + withinMs;
}

/** Group exams by local calendar day; return sorted groups (soonest first). */
export function groupExamsByTimelineDay(exams) {
  const map = new Map();

  for (const exam of exams || []) {
    const at = examTimelineDisplayAt(exam);
    const d = parseExamDate(at);
    if (!d) continue;

    const key = formatTimelineDayHeader(d);
    const sortKey = new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();

    if (!map.has(key)) {
      map.set(key, { sortKey, exams: [] });
    }
    map.get(key).exams.push(exam);
  }

  return Array.from(map.entries())
    .map(([key, value]) => ({ key, sortKey: value.sortKey, exams: value.exams }))
    .sort((a, b) => a.sortKey - b.sortKey);
}

/** Convert <input type="datetime-local"> value to UTC ISO for the API. */
export function localDatetimeInputToApi(value) {
  if (!value) return '';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toISOString();
}

/** Instructor dashboard: drafts with future schedule, or open/upcoming published exams. */
export function instructorExamOnDashboard(exam, { now = Date.now(), withinDays = 90 } = {}) {
  if (!exam) return false;

  if (!exam.is_final) {
    const due = parseExamDate(exam.due_at);
    const start = parseExamDate(exam.available_from);
    if (due && due.getTime() >= now) return passesTimelineWindow(exam, now, withinDays);
    if (start && start.getTime() >= now) return passesTimelineWindow(exam, now, withinDays);
    return false;
  }

  return passesTimelineWindow(exam, now, withinDays);
}

/** A submitted exam can be taken again only while attempts and time remain. */
export function canRetakeExam(exam, now = Date.now()) {
  if (!exam?.is_done || Number(exam.attempt_count || 1) >= Number(exam.max_attempts || 1)) return false;
  const start = parseExamDate(exam.available_from);
  const due = parseExamDate(exam.due_at);
  return (!start || start.getTime() <= now) && (!due || due.getTime() >= now);
}

/** Student dashboard: published, still open or upcoming, including available retakes. */
export function studentExamOnDashboard(exam, { now = Date.now(), withinDays = 90 } = {}) {
  if (!exam || (exam.is_done && !canRetakeExam(exam, now))) return false;
  if (exam.is_final === false) return false;
  return passesTimelineWindow(exam, now, withinDays);
}
