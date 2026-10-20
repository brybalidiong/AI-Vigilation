import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

// Run the production gaze loop with a deterministic camera, clock and socket.
const view = readFileSync(new URL('../src/views/StudentDashboardView.vue', import.meta.url), 'utf8');
const loop = view.slice(view.indexOf('let _gazeWs = null;'), view.indexOf('// Results modal (separate from taking modal)'));

function harness() {
  let now = 10000;
  let currentImage = 'frame-one';
  const sockets = [];
  const timers = new Map();
  const uploads = [];
  const direction = { value: '' };
  const preview = { value: '' };
  const display = { get direction() { return preview.value || direction.value; } };
  let directionEnabled = true;
  let timerId = 0;
  class Socket {
    static OPEN = 1;
    constructor() { this.readyState = 0; this.sent = []; sockets.push(this); }
    open() { this.readyState = 1; this.onopen(); }
    send(value) { this.sent.push(JSON.parse(value)); }
    close() { this.readyState = 3; this.onclose?.(); }
    reply(data = {}) {
      this.onmessage({ data: JSON.stringify({
        frame_id: this.sent.at(-1).frame_id, frame_receipt: 'signed-receipt',
        label: 'Looking at the left', face_detected: true, is_suspicious: true,
        ...data,
      }) });
    }
  }
  const context = vm.createContext({
    console, Blob, FormData, atob, URL, Uint8Array,
    Date: { now: () => now }, WebSocket: Socket,
    setTimeout: (fn, delay) => { timers.set(++timerId, { fn, delay }); return timerId; },
    clearTimeout: id => timers.delete(id),
    takingExam: { value: { id: 7 } }, examTerminated: { value: false }, submitting: { value: false },
    currentQuestion: { value: { id: 11, question_type: 'multiple_choice' } },
    gazeDetectionStatus: { value: '' }, gazeViolationCount: { value: 0 }, gazeNoFaceCount: { value: 0 },
    proctoringWarning: { value: { show: false } }, terminateReason: { value: '' },
    examVideoEl: { value: { readyState: 2, videoWidth: 640, videoHeight: 480 } },
    GAZE_WS_INTERVAL_MS: 0, GAZE_WS_BUSY_RETRY_MS: 100,
    GAZE_FRAME_WIDTH: 480, GAZE_VIOLATION_LIMIT: 8,
    backendBaseUrl: 'http://localhost:8000', window: { location: { protocol: 'http:' } },
    localStorage: { getItem: () => 'jwt' },
    document: { createElement: () => ({
      getContext: () => ({ drawImage() {} }),
      toDataURL: () => `data:image/jpeg;base64,${Buffer.from(currentImage).toString('base64')}`,
    }) },
    _updateGazeBbox() {}, _clearGazePending() {},
    gazeCurrentDirection: direction,
    gazePreviewDirection: preview,
    _isLeftRightLabel: label => /left|right/i.test(label) && !/left.*right|right.*left/i.test(label),
    _isGazeDirectionEnabled: () => directionEnabled,
    _startGazeViolationTimer: label => { direction.value = label; },
    _clearGazeViolationTimer: () => { direction.value = ''; },
    _formalGazeLabel: label => label, _terminateExam() {},
    api: { post: async (url, form) => { uploads.push({ url, form }); return { data: {} }; } },
  });
  vm.runInContext(loop, context);
  const run = code => vm.runInContext(code, context);
  run('_startGazeWsLoop()');
  sockets[0].open();
  return { run, context, sockets, timers, uploads, display,
    advance: ms => { now += ms; }, image: value => { currentImage = value; },
    setDirectionEnabled: enabled => { directionEnabled = enabled; } };
}

test('a slow stale reply is discarded without reconnecting or recording a violation', async () => {
  const h = harness();
  await h.run('_sendWsFrame()');
  assert.equal(h.sockets[0].sent.length, 1);
  h.sockets[0].reply();
  await h.run('_sendWsFrame()');
  assert.equal([...h.timers.values()].some(timer => timer.delay === 12000), true);
  h.advance(6000);
  h.sockets[0].reply();
  assert.equal(h.sockets[0].readyState, 1);
  assert.equal(h.run('_gazeWsActive'), true);
  assert.equal(h.run('_wsLatestFrame'), null);
  assert.equal(h.context.gazeDetectionStatus.value, 'AI delayed');
  assert.equal(h.display.direction, '');
  assert.equal(h.uploads.length, 0);
  assert.equal([...h.timers.values()].some(timer => timer.delay === 0), true);
  await h.run('_sendWsFrame()');
  h.sockets[0].reply({ label: 'Looking at the screen (Normal)', is_normal: true, is_suspicious: false });
  assert.equal(h.context.gazeDetectionStatus.value, '');
});

test('a busy worker requests a fresh frame without reconnecting or applying stale gaze', async () => {
  const h = harness();
  h.sockets[0].reply({ busy: true, frame_receipt: undefined });
  assert.equal(h.sockets[0].readyState, 1);
  assert.equal(h.run('_wsPendingFrame'), null);
  assert.equal(h.run('_wsLatestFrame'), null);
  assert.equal(h.display.direction, '');
  assert.equal(h.context.gazeDetectionStatus.value, 'AI busy');
  const retry = [...h.timers.values()].find(timer => timer.delay === 100);
  assert.ok(retry);
  h.image('fresh-frame');
  retry.fn();
  assert.equal(h.sockets[0].sent.length, 2);
  assert.equal(h.run('_wsPendingFrame.image').includes(Buffer.from('fresh-frame').toString('base64')), true);
});

test('a slow cold-start result is accepted within the startup timeout', () => {
  const h = harness();
  h.advance(12000);
  h.sockets[0].reply({
    label: 'Looking at the screen (Normal)', is_normal: true, is_suspicious: false,
  });
  assert.equal(h.sockets[0].readyState, 1);
  assert.equal(h.run('_gazeWsActive'), true);
  assert.equal(h.context.gazeDetectionStatus.value, '');
});

test('a first horizontal result updates the display before strike timing starts', async () => {
  const h = harness();
  h.sockets[0].reply({ stabilizing: true, is_suspicious: false });
  assert.equal(h.display.direction, 'Looking at the left');
  assert.equal(h.run('_wsViolationStartTime'), null);
  assert.equal(h.context.gazeCurrentDirection.value, '');
  assert.equal(h.uploads.length, 0);

  await h.run('_sendWsFrame()');
  h.sockets[0].reply();
  assert.equal(h.context.gazePreviewDirection.value, '');
  assert.equal(h.display.direction, 'Looking at the left');
  assert.equal(h.run('_wsViolationStartTime'), 10000);
});

test('a busy gap cannot turn one old suspicious frame into a strike', async () => {
  const h = harness();
  h.sockets[0].reply();
  assert.equal(h.run('_wsViolationStartTime'), 10000);

  await h.run('_sendWsFrame()');
  h.advance(2000);
  h.sockets[0].reply({ busy: true, frame_receipt: undefined });
  assert.equal(h.run('_wsViolationStartTime'), null);
  assert.equal(h.display.direction, '');

  await h.run('_sendWsFrame()');
  h.advance(2500);
  h.sockets[0].reply();
  assert.equal(h.run('_wsViolationStartTime'), 14500);
  assert.equal(h.uploads.length, 0);
});

test('a first rightward result appears immediately and an ensuing normal result clears its preview', async () => {
  const h = harness();
  h.sockets[0].reply({ label: 'Looking at the right', stabilizing: true, is_suspicious: false });
  assert.equal(h.display.direction, 'Looking at the right');
  assert.equal(h.run('_wsViolationStartTime'), null);

  await h.run('_sendWsFrame()');
  h.sockets[0].reply({ label: 'Looking at the screen (Normal)', is_normal: true, is_suspicious: false });
  assert.equal(h.display.direction, '');
  assert.equal(h.run('_wsViolationStartTime'), null);
});

test('up and down show on the first valid gaze result', () => {
  for (const label of ['Looking above', 'Looking below']) {
    const h = harness();
    h.sockets[0].reply({ label });
    assert.equal(h.display.direction, label);
    assert.equal(h.run('_wsViolationStartTime'), 10000);
  }
});

test('disabled directions and absence never show an early horizontal preview', () => {
  const local = harness();
  local.setDirectionEnabled(false);
  local.sockets[0].reply({ stabilizing: true, is_suspicious: false });
  assert.equal(local.display.direction, '');
  assert.equal(local.run('_wsViolationStartTime'), null);

  const server = harness();
  server.sockets[0].reply({ stabilizing: true, is_suspicious: false, direction_enabled: false });
  assert.equal(server.display.direction, '');
  assert.equal(server.run('_wsViolationStartTime'), null);

  const absent = harness();
  absent.sockets[0].reply({ stabilizing: true, is_suspicious: false, face_detected: false });
  assert.equal(absent.display.direction, '');
  assert.equal(absent.run('_wsViolationStartTime'), null);
});

test('evidence is the analyzed frame even if camera changes before response', async () => {
  const h = harness();
  assert.equal(h.context.gazeDetectionStatus.value, 'Starting AI');
  h.sockets[0].reply();
  assert.equal(h.context.gazeDetectionStatus.value, '');
  for (let i = 0; i < 3; i += 1) {
    h.advance(1000);
    await h.run('_sendWsFrame()');
    h.sockets[0].reply();
  }
  h.advance(1100);
  h.image('look-away-frame');
  await h.run('_sendWsFrame()');
  h.image('already-looking-back');
  h.sockets[0].reply();
  assert.equal(h.uploads.length, 1);
  assert.equal(await h.uploads[0].form.get('image').text(), 'look-away-frame');
  assert.equal(h.uploads[0].form.get('frame_receipt'), 'signed-receipt');
  assert.equal(h.display.direction, 'Looking at the left');
  await h.run('_sendWsFrame()');
  h.sockets[0].reply({ label: 'Looking at the screen (Normal)', is_normal: true, is_suspicious: false });
  assert.equal(h.display.direction, 'Looking at the left');
  await h.run('_sendWsFrame()');
  h.sockets[0].reply({ label: 'Looking at the screen (Normal)', is_normal: true, is_suspicious: false });
  assert.equal(h.display.direction, '');
});

test('no response closes the socket and stopping cancels pending frame timers', () => {
  const h = harness();
  [...h.timers.values()].find(timer => timer.delay === 20000).fn();
  assert.equal(h.run('_gazeWsActive'), false);
  h.run('_stopGazeWsLoop()');
  assert.equal(h.run('_wsPendingFrame'), null);
  assert.equal(h.run('_gazeWs'), null);
});

test('a server inference error is identified before frame validation', () => {
  const h = harness();
  h.sockets[0].onmessage({ data: JSON.stringify({ error: 'model unavailable' }) });
  assert.equal(h.run('_gazeWsActive'), false);
  assert.equal(h.run('_wsCloseCause'), 'server inference error');
});

test('a reply from an old exam socket cannot alter a new session', () => {
  const h = harness();
  const old = h.sockets[0];
  h.run('_stopGazeWsLoop(); _startGazeWsLoop()');
  h.sockets[1].open();
  old.reply();
  assert.equal(h.run('_wsLatestFrame'), null);
  assert.equal(h.run('_gazeWsActive'), true);
});
