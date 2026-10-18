export function isPhoneDevice(device = globalThis) {
  const navigator = device.navigator
  if (navigator?.userAgentData?.mobile === true) return true

  const userAgent = navigator?.userAgent || ''
  if (/iPhone|iPod|Windows Phone/i.test(userAgent)) return true
  if (/Android/i.test(userAgent) && /Mobile/i.test(userAgent)) return true

  const shortSide = Math.min(device.screen?.width ?? Infinity, device.screen?.height ?? Infinity)
  return shortSide <= 600 && device.matchMedia?.('(pointer: coarse)')?.matches === true
}
