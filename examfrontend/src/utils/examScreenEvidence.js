/** Capture a shared monitor frame while the exam page is away from focus. */
export async function captureSharedDisplayImage({ track, video, doc, isAway = () => true, requireAway = true, ImageCaptureCtor = globalThis.ImageCapture }) {
  if (!track || track.readyState !== 'live' || (requireAway && !isAway())) return null;
  let frame = null;
  if (typeof ImageCaptureCtor === 'function') {
    let timedOut = false;
    let timeoutId;
    try {
      const grab = new ImageCaptureCtor(track).grabFrame().then((bitmap) => {
        if (timedOut) bitmap.close();
        return timedOut ? null : bitmap;
      });
      frame = await Promise.race([
        grab,
        new Promise((resolve) => {
          timeoutId = setTimeout(() => { timedOut = true; resolve(null); }, 1800);
        }),
      ]);
    } catch {
      // Older browsers can still use the visible-window video preview below.
    } finally {
      clearTimeout(timeoutId);
    }
  }
  if (!frame && !doc.hidden && video?.videoWidth) frame = video;
  if (!frame || (requireAway && (!isAway() || (!doc.hidden && doc.hasFocus())))) {
    frame?.close?.();
    return null;
  }

  const frameWidth = frame.width || frame.videoWidth;
  const frameHeight = frame.height || frame.videoHeight;
  const canvas = doc.createElement('canvas');
  canvas.width = Math.min(1280, frameWidth);
  canvas.height = Math.round(frameHeight * canvas.width / frameWidth);
  canvas.getContext('2d')?.drawImage(frame, 0, 0, canvas.width, canvas.height);
  frame.close?.();
  return new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.78));
}
