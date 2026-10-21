/** Keep one departure open until the exam page becomes visible and focused again. */
export function attachExamWindowMonitor({ doc, win, onLeave, onReturn, onHidden }) {
  let away = false;

  const leave = (source) => {
    if (away) return;
    away = true;
    onLeave(source);
  };
  const returnToExam = (source) => {
    if (!away || doc.hidden) return;
    away = false;
    onReturn(source);
  };
  const visibilityHandler = () => {
    if (doc.hidden) {
      leave('visibilitychange');
      onHidden();
    } else {
      returnToExam('visibilitychange');
    }
  };
  const blurHandler = () => leave('blur');
  const focusHandler = () => returnToExam('focus');

  doc.addEventListener('visibilitychange', visibilityHandler);
  win.addEventListener('blur', blurHandler);
  win.addEventListener('focus', focusHandler);

  return () => {
    doc.removeEventListener('visibilitychange', visibilityHandler);
    win.removeEventListener('blur', blurHandler);
    win.removeEventListener('focus', focusHandler);
  };
}
