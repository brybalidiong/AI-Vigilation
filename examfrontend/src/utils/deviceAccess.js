export function isUnsupportedDevice(device = globalThis) {
  const navigator = device.navigator
  if (navigator?.userAgentData?.mobile === true) return true

  const userAgent = navigator?.userAgent || ''
  if (/iPhone|iPod|iPad|Windows Phone|Android/i.test(userAgent)) return true

  // iPadOS uses a Macintosh user agent when "Request Desktop Website" is enabled.
  if ((/Macintosh/i.test(userAgent) || /^Mac/i.test(navigator?.platform || ''))
    && (navigator?.maxTouchPoints ?? 0) > 1) return true

  const shortSide = Math.min(device.screen?.width ?? Infinity, device.screen?.height ?? Infinity)
  return shortSide <= 600 && device.matchMedia?.('(pointer: coarse)')?.matches === true
}
