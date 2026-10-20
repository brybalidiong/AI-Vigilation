import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const view = readFileSync(new URL('../src/views/StudentDashboardView.vue', import.meta.url), 'utf8');
const loop = view.slice(view.indexOf('async function _runGadgetDetection()'), view.indexOf('async function _runGazeCheck()'));

function harness() {
  const timers = new Map();
  const requests = [];
  const rejectRequests = [];
  let timerId = 0;
  const context = vm.createContext({
    Date, FormData, console,
    setTimeout: (fn, delay) => { timers.set(++timerId, { fn, delay }); return timerId; },
    clearTimeout: id => timers.delete(id),
    takingExam: { value: { id: 1 } }, examTerminated: { value: false }, submitting: { value: false },
    currentQuestion: { value: { id: 2 } },
    gadgetDetectionStatus: { value: 'starting' }, gadgetWarningCount: { value: 0 },
    proctoringWarning: { value: { show: false } },
    terminateReason: { value: '' },
    GADGET_IDLE_POLL_MS: 150, GADGET_ACTIVE_POLL_MS: 100,
    GADGET_VISIBLE_POLL_MS: 300, GADGET_ERROR_POLL_MS: 500, GADGET_FRAME_WIDTH: 640,
    GADGET_WARNING_LIMIT: 3,
    _isGadgetDetectionEnabled: () => true,
    _getProctoringVideoEl: () => ({ readyState: 2, videoWidth: 640, videoHeight: 480 }),
    document: { createElement: () => ({
      getContext: () => ({ drawImage() {} }),
      toBlob: resolve => resolve(new Blob(['synthetic frame'], { type: 'image/jpeg' })),
    }) },
    api: { post: () => new Promise((resolve, reject) => {
      requests.push(resolve);
      rejectRequests.push(reject);
    }) },
    showToastMessage() {}, _terminateExam() {},
  });
  vm.runInContext(`let _gadgetDetectionTimer = null;
    let _gadgetDetectionInFlight = false;
    let _gadgetUnavailableNotified = false;
    let _gadgetFailureCount = 0;
    let _gadgetLoopActive = false;
    let _gadgetLoopGeneration = 0;
    let _gadgetCaptureCanvas = null;
    ${loop}`, context);
  return { context, timers, requests, rejectRequests, run: code => vm.runInContext(code, context) };
}

test('warns on the first positive response and schedules the next fresh frame promptly', async () => {
  const h = harness();
  h.run('_startGadgetDetectionTimer()');
  await Promise.resolve();
  assert.equal(h.requests.length, 1);
  assert.equal(h.run('_gadgetDetectionInFlight'), true);
  h.requests[0]({ data: {
    detections: [{ label: 'cell phone', box: [1, 2, 30, 40] }],
    warning_count: 1, warning_limit: 3, confirmed: true, detected: true,
  } });
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(h.context.proctoringWarning.value.type, 'gadget');
  assert.equal(h.context.gadgetWarningCount.value, 1);
  assert.ok([...h.timers.values()].some(timer => timer.delay === 300));
});

test('a clear frame resumes rapid scanning without overlapping requests', async () => {
  const h = harness();
  h.run('_startGadgetDetectionTimer()');
  await Promise.resolve();
  h.requests[0]({ data: { detections: [], detected: false, warning_count: 0 } });
  await new Promise(resolve => setImmediate(resolve));
  const next = [...h.timers.values()].find(timer => timer.delay === 100);
  assert.ok(next);
  next.fn();
  await Promise.resolve();
  assert.equal(h.requests.length, 2);
});

test('a busy detector retries without reporting it unavailable', async () => {
  const h = harness();
  h.run('_startGadgetDetectionTimer()');
  await Promise.resolve();
  h.rejectRequests[0]({ response: { status: 429 } });
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(h.context.gadgetDetectionStatus.value, 'busy');
  assert.equal(h.run('_gadgetFailureCount'), 0);
  assert.ok([...h.timers.values()].some(timer => timer.delay === 150));
});

test('a late response from a stopped exam cannot change a new exam', async () => {
  const h = harness();
  h.run('_startGadgetDetectionTimer()');
  await Promise.resolve();
  h.run('_stopGadgetDetectionTimer(); _startGadgetDetectionTimer()');
  await Promise.resolve();
  h.requests[0]({ data: { detections: [], warning_count: 2, confirmed: true } });
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(h.context.gadgetWarningCount.value, 0);
  assert.equal(h.context.proctoringWarning.value.show, false);
  assert.equal(h.run('_gadgetDetectionInFlight'), true);
  assert.equal(h.requests.length, 2);
});
