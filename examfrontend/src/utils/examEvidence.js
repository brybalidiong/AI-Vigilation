const captionOf = (shot) => String(shot?.caption || '').trim();

const isSnapshot = (shot) => /^(scheduled webcam snapshot|exam session start snapshot)/i.test(captionOf(shot));
const isTermination = (shot) => /^exam auto-terminated\b/i.test(captionOf(shot));
const isViolation = (shot) => /^(gadget ai:|gaze ai:|gaze violation:|face not visible)/i.test(captionOf(shot));

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
  if (/^gadget ai:/i.test(caption)) return 'Gadget';
  if (/^(gaze ai:|gaze violation:)/i.test(caption)) return 'Gaze';
  if (/^face not visible/i.test(caption)) return 'Face';
  if (/^exam session start snapshot/i.test(caption)) return 'Exam start';
  if (/^scheduled webcam snapshot/i.test(caption)) return 'Routine';
  if (isTermination(shot)) return 'Exam end';
  return shot?.evidence_type === 'screen' ? 'Screen' : 'Webcam';
}

export function evidenceDescription(shot) {
  const caption = captionOf(shot);
  if (/^gadget ai:/i.test(caption)) {
    const item = caption.replace(/^gadget ai:\s*/i, '').trim();
    return item ? `${item[0].toUpperCase()}${item.slice(1)} detected` : 'Gadget detected';
  }
  if (/^(gaze ai:|gaze violation:)/i.test(caption)) {
    return caption.replace(/^(gaze ai:|gaze violation:)\s*/i, '')
      .replace(/^looking at the /i, 'Looking ')
      .replace(/^looking above the screen$/i, 'Looking above screen')
      .replace(/^looking below the screen$/i, 'Looking below screen') || 'Looking away';
  }
  if (/^face not visible/i.test(caption)) return 'Face not visible';
  if (/^exam session start snapshot/i.test(caption)) return 'Exam started';
  if (/^scheduled webcam snapshot/i.test(caption)) return 'Routine webcam check';
  if (isTermination(shot)) return 'Exam ended after a proctoring violation';
  return caption || 'Webcam capture';
}
