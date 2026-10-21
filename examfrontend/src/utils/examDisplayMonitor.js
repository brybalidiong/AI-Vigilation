/** Detect connected displays; the browser does not reveal activity on another display. */
export function hasExtendedDisplay(screen, details) {
  if (Array.isArray(details?.screens)) return details.screens.length > 1;
  return screen?.isExtended === true;
}

export function watchExtendedDisplays({ win, details, onChange, intervalMs = 2000 }) {
  const check = () => onChange(hasExtendedDisplay(win.screen, details));
  details?.addEventListener?.('screenschange', check);
  win.screen?.addEventListener?.('change', check);
  const timer = win.setInterval(check, intervalMs);
  check();
  return () => {
    win.clearInterval(timer);
    details?.removeEventListener?.('screenschange', check);
    win.screen?.removeEventListener?.('change', check);
  };
}
