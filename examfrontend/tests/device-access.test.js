import assert from 'node:assert/strict'
import test from 'node:test'

import { isUnsupportedDevice } from '../src/utils/deviceAccess.js'

function device(userAgent, width, height, { coarse = true, mobile, platform, maxTouchPoints = 0 } = {}) {
  return {
    navigator: { userAgent, platform, maxTouchPoints, userAgentData: mobile === undefined ? undefined : { mobile } },
    screen: { width, height },
    matchMedia: () => ({ matches: coarse }),
  }
}

test('blocks phones in portrait, landscape, and desktop site mode', () => {
  assert.equal(isUnsupportedDevice(device('Mozilla/5.0 (iPhone; CPU iPhone OS 18_0)', 390, 844)), true)
  assert.equal(isUnsupportedDevice(device('Mozilla/5.0 (Linux; Android 15; Pixel 9) AppleWebKit Mobile', 915, 412)), true)
  assert.equal(isUnsupportedDevice(device('Mozilla/5.0 (Macintosh; Intel Mac OS X)', 390, 844)), true)
  assert.equal(isUnsupportedDevice(device('Mozilla/5.0', 1080, 2400, { mobile: true })), true)
})

test('blocks tablets, including large iPads requesting desktop mode', () => {
  assert.equal(isUnsupportedDevice(device('Mozilla/5.0 (iPad; CPU OS 18_0)', 820, 1180)), true)
  assert.equal(isUnsupportedDevice(device('Mozilla/5.0 (Linux; Android 15; Tablet)', 800, 1280)), true)
  assert.equal(isUnsupportedDevice(device('Mozilla/5.0 (Macintosh; Intel Mac OS X)', 1032, 1376,
    { platform: 'MacIntel', maxTouchPoints: 5, coarse: false })), true)
  assert.equal(isUnsupportedDevice(device('Mozilla/5.0 (Macintosh; Intel Mac OS X)', 1024, 1366,
    { maxTouchPoints: 5 })), true)
})

test('allows desktop browsers, including touch-enabled Windows laptops', () => {
  assert.equal(isUnsupportedDevice(device('Mozilla/5.0 (Windows NT 10.0; Win64; x64)', 1920, 1080,
    { coarse: false })), false)
  assert.equal(isUnsupportedDevice(device('Mozilla/5.0 (Windows NT 10.0; Win64; x64)', 1920, 1080,
    { platform: 'Win32', maxTouchPoints: 10 })), false)
  assert.equal(isUnsupportedDevice(device('Mozilla/5.0 (Macintosh; Intel Mac OS X)', 1512, 982,
    { platform: 'MacIntel' })), false)
})
