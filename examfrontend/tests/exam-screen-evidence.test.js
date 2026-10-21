import test from 'node:test';
import assert from 'node:assert/strict';
import { captureSharedDisplayImage } from '../src/utils/examScreenEvidence.js';

test('a hidden exam tab captures the shared monitor track without the preview video', async () => {
  const track = { readyState: 'live' };
  const calls = [];
  const bitmap = { width: 1920, height: 1080, close: () => calls.push('closed') };
  class ImageCapture {
    constructor(source) { assert.equal(source, track); }
    grabFrame() { return Promise.resolve(bitmap); }
  }
  const doc = {
    hidden: true,
    hasFocus: () => false,
    createElement: () => ({
      getContext: () => ({ drawImage: () => calls.push('drawn') }),
      toBlob: (resolve) => resolve(new Blob(['synthetic frame'], { type: 'image/jpeg' })),
    }),
  };

  const blob = await captureSharedDisplayImage({ track, video: null, doc, isAway: () => true, ImageCaptureCtor: ImageCapture });
  assert.equal(blob?.type, 'image/jpeg');
  assert.deepEqual(calls, ['drawn', 'closed']);
});

test('a frame arriving after the student returns is discarded', async () => {
  let resolveFrame;
  let away = true;
  let closed = false;
  class ImageCapture {
    grabFrame() { return new Promise((resolve) => { resolveFrame = resolve; }); }
  }
  const doc = { hidden: false, hasFocus: () => true };
  const capture = captureSharedDisplayImage({
    track: { readyState: 'live' }, doc, isAway: () => away, ImageCaptureCtor: ImageCapture,
  });
  away = false;
  resolveFrame({ width: 640, height: 480, close: () => { closed = true; } });
  assert.equal(await capture, null);
  assert.equal(closed, true);
});
