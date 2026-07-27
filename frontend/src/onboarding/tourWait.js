export function waitForSelector(selector, { timeoutMs = 2500 } = {}) {
  if (!selector) return Promise.resolve(true);
  return new Promise((resolve) => {
    const start = performance.now();
    function tick() {
      if (document.querySelector(selector)) {
        resolve(true);
        return;
      }
      if (performance.now() - start > timeoutMs) {
        resolve(false);
        return;
      }
      window.requestAnimationFrame(tick);
    }
    tick();
  });
}
