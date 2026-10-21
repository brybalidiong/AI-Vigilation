import test from 'node:test';
import assert from 'node:assert/strict';
import { attachExamWindowMonitor } from '../src/utils/examWindowMonitor.js';

function browserEvents() {
  const doc = new EventTarget();
  const win = new EventTarget();
  doc.hidden = false;
  doc.focused = true;
  doc.hasFocus = () => doc.focused;
  return { doc, win };
}

test('tab change records a departure on blur before visibility becomes hidden', () => {
  const { doc, win } = browserEvents();
  const calls = [];
  const stop = attachExamWindowMonitor({
    doc, win,
    onLeave: (source) => calls.push(['leave', source]),
    onHidden: () => calls.push(['capture']),
    onReturn: (source) => calls.push(['return', source]),
  });

  win.dispatchEvent(new Event('blur'));
  assert.deepEqual(calls, [['leave', 'blur']]);
  doc.hidden = true;
  doc.dispatchEvent(new Event('visibilitychange'));
  assert.deepEqual(calls, [['leave', 'blur'], ['capture']]);
  doc.hidden = false;
  doc.dispatchEvent(new Event('visibilitychange'));
  win.dispatchEvent(new Event('focus'));
  assert.deepEqual(calls, [['leave', 'blur'], ['capture'], ['return', 'visibilitychange']]);
  stop();
});

test('brief tab change still records once even if visibility events are delayed', () => {
  const { doc, win } = browserEvents();
  const calls = [];
  const stop = attachExamWindowMonitor({
    doc, win,
    onLeave: (source) => calls.push(['leave', source]),
    onHidden: () => calls.push(['capture']),
    onReturn: (source) => calls.push(['return', source]),
  });

  win.dispatchEvent(new Event('blur'));
  win.dispatchEvent(new Event('focus'));
  assert.deepEqual(calls, [['leave', 'blur'], ['return', 'focus']]);
  stop();
  win.dispatchEvent(new Event('blur'));
  assert.equal(calls.length, 2);
});

test('visible tab does not close a departure until the exam regains focus', () => {
  const { doc, win } = browserEvents();
  const calls = [];
  const stop = attachExamWindowMonitor({
    doc, win,
    onLeave: (source) => calls.push(['leave', source]),
    onHidden: () => {},
    onReturn: (source) => calls.push(['return', source]),
  });
  doc.focused = false;
  win.dispatchEvent(new Event('blur'));
  doc.hidden = true;
  doc.dispatchEvent(new Event('visibilitychange'));
  doc.hidden = false;
  doc.dispatchEvent(new Event('visibilitychange'));
  win.dispatchEvent(new Event('blur'));
  assert.deepEqual(calls, [['leave', 'blur']]);
  doc.focused = true;
  win.dispatchEvent(new Event('focus'));
  assert.deepEqual(calls, [['leave', 'blur'], ['return', 'focus']]);
  stop();
});
