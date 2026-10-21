const captionOf = (shot) => String(shot?.caption || '').trim();

const isSnapshot = (shot) => /^(scheduled webcam snapshot|exam session start snapshot)/i.test(captionOf(shot));
const isTermination = (shot) => /^exam auto-terminated\b/i.test(captionOf(shot));
const isViolation = (shot) => /^(gadget ai:|gaze ai:|gaze violation:|face not visible|screen shown after leaving exam window|shared display captured after leaving the exam window)/i.test(captionOf(shot));

export function groupExamEvidence(records) {
  const all = Array.isArray(records) ? records : [];
  const snapshots = all.filter(isSnapshot);
  const captures = all.filter((shot) => !isSnapshot(shot) && !isTermination(shot));
  const terminations = all.filter(isTermination);
  // The logged termination remains in the action log. Keep one final image
  // only when there is no violation image showing why the exam ended.
  const evidence = captures.some(isViolation)
    ? captures
    : [...captures, ...terminations.slice(-1)];
  return { evidence, snapshots };
}

export function evidenceCategory(shot) {
  const caption = captionOf(shot);
  if (/^(screen shown after leaving exam window|shared display captured after leaving the exam window)/i.test(caption)) return 'Exam window left';
  if (/^gadget ai:/i.test(caption)) return 'Gadget detection';
  if (/^(gaze ai:|gaze violation:)/i.test(caption)) return 'Gaze deviation';
  if (/^face not visible/i.test(caption)) return 'Face visibility';
  if (/^exam session start snapshot/i.test(caption)) return 'Exam session start';
  if (/^scheduled webcam snapshot/i.test(caption)) return 'Scheduled webcam capture';
  if (isTermination(shot)) return 'Exam termination';
  return shot?.evidence_type === 'screen' ? 'Screen capture' : 'Webcam capture';
}

export function evidenceDescription(shot) {
  const caption = captionOf(shot);
  if (/^(screen shown after leaving exam window|shared display captured after leaving the exam window)/i.test(caption)) return 'Shared display captured after the student left the exam window';
  if (/^gadget ai:/i.test(caption)) {
    const item = caption.replace(/^gadget ai:\s*/i, '').trim();
    return item ? `Prohibited ${item.toLowerCase()} detected during the exam` : 'Prohibited gadget detected during the exam';
  }
  if (/^(gaze ai:|gaze violation:)/i.test(caption)) {
    const direction = caption.replace(/^(gaze ai:|gaze violation:)\s*/i, '')
      .replace(/^looking at the /i, '')
      .replace(/^looking /i, '')
      .replace(/ the screen$/i, '')
      .trim().toLowerCase();
    return direction ? `Student looked ${direction} during the exam` : 'Student looked away from the exam screen';
  }
  if (/^face not visible/i.test(caption)) return "Student's face was not visible to the camera";
  if (/^exam session start snapshot/i.test(caption)) return 'Webcam capture at the start of the exam';
  if (/^scheduled webcam snapshot/i.test(caption)) return 'Scheduled webcam capture during the exam';
  if (isTermination(shot)) return 'Webcam capture at automatic exam termination';
  return caption || (shot?.evidence_type === 'screen' ? 'Screen capture during the exam' : 'Webcam capture during the exam');
}
