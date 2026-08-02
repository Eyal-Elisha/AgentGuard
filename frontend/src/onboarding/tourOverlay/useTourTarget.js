import { useLayoutEffect, useState } from 'react';
import { measureTarget } from './geometry.js';

export function useTourTarget({ isOpen, step, stepIndex, locationPath }) {
  const [target, setTarget] = useState(null);

  useLayoutEffect(() => {
    if (!isOpen || !step) {
      setTarget(null);
      return undefined;
    }

    let cancelled = false;
    let tries = 0;

    const update = () => {
      if (cancelled) return;
      const measured = measureTarget(step.selector);
      setTarget(measured);
      if (!measured && step.selector && tries < 40) {
        tries += 1;
        window.requestAnimationFrame(update);
      }
    };

    update();
    window.addEventListener('resize', update);
    window.addEventListener('scroll', update, true);
    const id = window.setInterval(update, 200);
    return () => {
      cancelled = true;
      window.removeEventListener('resize', update);
      window.removeEventListener('scroll', update, true);
      window.clearInterval(id);
    };
  }, [isOpen, step, stepIndex, locationPath]);

  return target;
}
