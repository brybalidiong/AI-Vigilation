import test from 'node:test';
import assert from 'node:assert/strict';
import { hasExtendedDisplay, watchExtendedDisplays } from '../src/utils/examDisplayMonitor.js';

test('screen details take precedence over a stale single-screen flag', () => {
  assert.equal(hasExtendedDisplay({ isExtended: false }, { screens: [{}, {}] }), true);
  assert.equal(hasExtendedDisplay({ isExtended: true }, { screens: [{}] }), false);
  assert.equal(hasExtendedDisplay({ isExtended: true }, null), true);
});

test('connecting and disconnecting a display updates the exam warning', () => {
  const details = new EventTarget();
  details.screens = [{}];
  const screen = new EventTarget();
  screen.isExtended = false;
  let checkInterval;
  let cleared = false;
  const win = {
    screen,
    setInterval: (callback) => { checkInterval = callback; return 1; },
    clearInterval: (id) => { assert.equal(id, 1); cleared = true; },
  };
  const states = [];
  const stop = watchExtendedDisplays({ win, details, onChange: (state) => states.push(state) });
  details.screens.push({});
  details.dispatchEvent(new Event('screenschange'));
  details.screens.pop();
  checkInterval();
  assert.deepEqual(states, [false, true, false]);
  stop();
  assert.equal(cleared, true);
});
