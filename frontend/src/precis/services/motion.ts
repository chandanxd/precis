/**
 * Pause the background animations while the tab is hidden or the window is not
 * focused, so an idle Précis tab does not keep the CPU and GPU busy. Sets
 * data-motion="paused" | "running" on <html>; precis.css pauses every animation
 * while it is "paused". Returns a function that stops watching.
 */
export function watchMotion(): () => void {
  const update = () => {
    const paused = document.hidden || !document.hasFocus();
    document.documentElement.setAttribute("data-motion", paused ? "paused" : "running");
  };
  update();
  document.addEventListener("visibilitychange", update);
  window.addEventListener("blur", update);
  window.addEventListener("focus", update);
  return () => {
    document.removeEventListener("visibilitychange", update);
    window.removeEventListener("blur", update);
    window.removeEventListener("focus", update);
  };
}
