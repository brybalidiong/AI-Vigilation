import test from 'node:test';
import assert from 'node:assert/strict';
import { evidenceCategory, evidenceDescription, groupExamEvidence } from '../src/utils/examEvidence.js';

test('review gallery keeps violation captures and moves exam start into snapshots', () => {
  const records = [
    { id: 1, caption: 'Exam session start snapshot' },
    { id: 2, caption: 'Gadget AI: cell phone' },
    { id: 3, caption: 'Gaze AI: Looking at the right' },
    { id: 4, caption: 'Gadget AI: cell phone' },
    { id: 5, caption: 'Gadget AI: cell phone' },
    { id: 6, caption: 'Exam auto-terminated (gadget)' },
    { id: 7, caption: 'Exam auto-terminated (gadget)' },
    { id: 8, caption: 'Exam auto-terminated (gadget)' },
  ];
  const grouped = groupExamEvidence(records);
  assert.deepEqual(grouped.evidence.map((shot) => shot.id), [2, 3, 4, 5]);
  assert.deepEqual(grouped.snapshots.map((shot) => shot.id), [1]);
  assert.equal(records.length, 8);
});

test('last termination capture remains visible when no violation image was recorded', () => {
  const grouped = groupExamEvidence([
    { id: 1, caption: 'Exam session start snapshot' },
    { id: 2, caption: 'Exam auto-terminated (tab switches)' },
    { id: 3, caption: 'Exam auto-terminated (tab switches)' },
  ]);
  assert.deepEqual(grouped.evidence.map((shot) => shot.id), [3]);
});

test('evidence cards identify the event and preserve distinct capture times', () => {
  const gadget = { caption: 'Gadget AI: cell phone' };
  const gaze = { caption: 'Gaze AI: Looking at the right' };
  assert.equal(evidenceCategory(gadget), 'Gadget');
  assert.equal(evidenceDescription(gadget), 'Cell phone detected');
  assert.equal(evidenceCategory(gaze), 'Gaze');
  assert.equal(evidenceDescription(gaze), 'Looking right');
  assert.equal(evidenceDescription({ caption: 'Exam session start snapshot' }), 'Exam started');
});
