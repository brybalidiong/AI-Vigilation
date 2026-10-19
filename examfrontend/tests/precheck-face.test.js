import test from 'node:test';
import assert from 'node:assert/strict';
import { classifyPrecheckFace, nextPrecheckFaceState } from '../src/utils/precheckFace.js';

test('accepts a single clearly visible face', () => {
  assert.equal(classifyPrecheckFace({ face_detected: true, label: 'normal', face_bbox: [0.3, 0.2, 0.7, 0.7] }), 'ready');
});

test('blocks a distant or undetected face', () => {
  assert.equal(classifyPrecheckFace({ face_detected: true, label: 'normal', face_bbox: [0.42, 0.35, 0.55, 0.55] }), 'too_far');
  assert.equal(classifyPrecheckFace({ face_detected: false, label: 'no_face' }), 'too_far');
});

test('blocks multiple faces and missing model measurements', () => {
  assert.equal(classifyPrecheckFace({ face_detected: true, label: 'multiple_people' }), 'multiple_faces');
  assert.equal(classifyPrecheckFace({ face_detected: true, label: 'normal' }), 'unavailable');
  assert.equal(classifyPrecheckFace({ face_detected: false, label: 'gaze_model_unavailable' }), 'unavailable');
  assert.equal(classifyPrecheckFace({ face_detected: true, label: 'normal', face_bbox: [0, 0, 2, 1] }), 'unavailable');
});

test('requires two consecutive usable frames and revokes readiness immediately', () => {
  const clearFace = { face_detected: true, label: 'normal', face_bbox: [0.3, 0.2, 0.7, 0.7] };
  const first = nextPrecheckFaceState(0, clearFace);
  assert.deepEqual(first, { readyStreak: 1, faceVisible: false, status: 'checking' });
  const second = nextPrecheckFaceState(first.readyStreak, clearFace);
  assert.deepEqual(second, { readyStreak: 2, faceVisible: true, status: 'ready' });
  assert.deepEqual(nextPrecheckFaceState(second.readyStreak, { face_detected: false, label: 'no_face' }), {
    readyStreak: 0, faceVisible: false, status: 'too_far',
  });
});
