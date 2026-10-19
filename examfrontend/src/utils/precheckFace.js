// Face boxes from the gaze socket are [x1, y1, x2, y2] relative to the frame.
// A face smaller than this is likely to disappear during the exam as the student moves.
export const MIN_PRECHECK_FACE_WIDTH = 0.16;
export const MIN_PRECHECK_FACE_HEIGHT = 0.22;

export function classifyPrecheckFace(result) {
  if (!result || result.error || result.label === 'error' || result.label === 'gaze_model_unavailable') {
    return 'unavailable';
  }
  if (result.label === 'multiple_people') return 'multiple_faces';
  if (!result.face_detected || result.label === 'no_face') return 'too_far';

  const box = result.face_bbox;
  if (!Array.isArray(box) || box.length !== 4 || !box.every(Number.isFinite)) {
    return 'unavailable';
  }
  const [x1, y1, x2, y2] = box;
  if (x1 < 0 || y1 < 0 || x2 > 1 || y2 > 1 || x2 <= x1 || y2 <= y1) {
    return 'unavailable';
  }
  return x2 - x1 < MIN_PRECHECK_FACE_WIDTH || y2 - y1 < MIN_PRECHECK_FACE_HEIGHT
    ? 'too_far'
    : 'ready';
}

export function nextPrecheckFaceState(readyStreak, result) {
  const status = classifyPrecheckFace(result);
  const nextStreak = status === 'ready' ? readyStreak + 1 : 0;
  return {
    readyStreak: nextStreak,
    faceVisible: nextStreak >= 2,
    status: status === 'ready' && nextStreak < 2 ? 'checking' : status,
  };
}
