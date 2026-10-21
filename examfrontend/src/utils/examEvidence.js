const captionOf = (shot) => String(shot?.caption || '').trim();

const isSnapshot = (shot) => /^(scheduled webcam snapshot|exam session start snapshot)/i.test(captionOf(shot));
const isTermination = (shot) => /^exam auto-terminated\b/i.test(captionOf(shot));
const isViolation = (shot) => /^(gadget ai:|gaze ai:|gaze violation:|face not visible|switched tabs|screenshot attempt|split-screen detected|screen shown after leaving exam window|shared display captured after leaving the exam window)/i.test(captionOf(shot));

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
  if (/^(switched tabs|screenshot attempt|split-screen detected|screen shown after leaving exam window|shared display captured after leaving the exam window)/i.test(caption)) return 'SCREEN';
  return shot?.evidence_type === 'screen' ? 'SCREEN' : 'WEBCAM';
}

export function evidenceDescription(shot) {
  const caption = captionOf(shot);
  if (/^switched tabs/i.test(caption)) return 'Switched tabs';
  if (/^screenshot attempt/i.test(caption)) return 'Screenshot attempt';
  if (/^split-screen detected/i.test(caption)) return 'Split-screen detected';
  if (/^(screen shown after leaving exam window|shared display captured after leaving the exam window)/i.test(caption)) return 'Switched tabs';
  if (/^gadget ai:/i.test(caption)) {
    const item = caption.replace(/^gadget ai:\s*/i, '').trim();
    return item ? `${item.charAt(0).toUpperCase()}${item.slice(1).toLowerCase()} detected` : 'Gadget detected';
  }
  if (/^(gaze ai:|gaze violation:)/i.test(caption)) {
    const direction = caption.replace(/^(gaze ai:|gaze violation:)\s*/i, '')
      .replace(/^looking at the /i, '')
      .replace(/^looking /i, '')
      .replace(/ the screen$/i, '')
      .trim().toLowerCase();
    return direction ? `Looked ${direction}` : 'Looked away';
  }
  if (/^face not visible/i.test(caption)) return 'Face not visible';
  if (/^exam session start snapshot/i.test(caption)) return 'Exam started';
  if (/^scheduled webcam snapshot/i.test(caption)) return 'Scheduled capture';
  if (isTermination(shot)) return 'Exam terminated';
  return caption || (shot?.evidence_type === 'screen' ? 'Screen captured' : 'Webcam captured');
}
