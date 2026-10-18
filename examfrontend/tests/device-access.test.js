import assert from 'node:assert/strict'
import test from 'node:test'

import { isPhoneDevice } from '../src/utils/deviceAccess.js'

function device(userAgent, width, height, coarse = true, mobile) {
  return {
    navigator: { userAgent, userAgentData: mobile === undefined ? undefined : { mobile } },
    screen: { width, height },
    matchMedia: () => ({ matches: coarse }),
  }
}

test('blocks phones in portrait, landscape, and desktop site mode', () => {
  assert.equal(isPhoneDevice(device('Mozilla/5.0 (iPhone; CPU iPhone OS 18_0)', 390, 844)), true)
  assert.equal(isPhoneDevice(device('Mozilla/5.0 (Linux; Android 15; Pixel 9) AppleWebKit Mobile', 915, 412)), true)
  assert.equal(isPhoneDevice(device('Mozilla/5.0 (Macintosh; Intel Mac OS X)', 390, 844)), true)
  assert.equal(isPhoneDevice(device('Mozilla/5.0', 1080, 2400, true, true)), true)
})

test('allows desktop browsers and tablets', () => {
  assert.equal(isPhoneDevice(device('Mozilla/5.0 (Windows NT 10.0; Win64; x64)', 1920, 1080, false)), false)
  assert.equal(isPhoneDevice(device('Mozilla/5.0 (iPad; CPU OS 18_0)', 820, 1180)), false)
  assert.equal(isPhoneDevice(device('Mozilla/5.0 (Linux; Android 15; Tablet)', 800, 1280)), false)
})
