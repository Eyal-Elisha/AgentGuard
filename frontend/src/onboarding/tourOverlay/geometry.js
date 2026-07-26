export const POPOVER_EST_HEIGHT = 200;
export const POPOVER_GAP = 14;
export const SPOTLIGHT_PAD = 6;
const TALL_TARGET_CAP = 120;
const TALL_TARGET_THRESHOLD = 140;

export function measureTarget(selector) {
  if (!selector) return null;
  const el = document.querySelector(selector);
  if (!el) return null;
  const rect = el.getBoundingClientRect();
  if (rect.width === 0 && rect.height === 0) return null;
  const height = rect.height > TALL_TARGET_THRESHOLD
    ? Math.min(rect.height, TALL_TARGET_CAP)
    : rect.height;
  const nearSquare = Math.abs(rect.width - height) < 8;
  return {
    top: rect.top,
    left: rect.left,
    width: rect.width,
    height,
    round: nearSquare,
  };
}

export function computePopoverStyle(hole) {
  if (!hole) return undefined;

  const spaceBelow = window.innerHeight - (hole.top + hole.height);
  const spaceAbove = hole.top;
  const preferBelow = spaceBelow >= POPOVER_EST_HEIGHT || spaceBelow >= spaceAbove;

  let top;
  let transform;
  if (preferBelow) {
    top = hole.top + hole.height + POPOVER_GAP;
    transform = 'translate(-50%, 0)';
    if (top + POPOVER_EST_HEIGHT > window.innerHeight - 16) {
      top = Math.max(16, window.innerHeight - POPOVER_EST_HEIGHT - 16);
      transform = 'translate(-50%, 0)';
    }
  } else {
    top = Math.max(16, hole.top - POPOVER_GAP);
    transform = 'translate(-50%, -100%)';
    if (top - POPOVER_EST_HEIGHT < 16) {
      top = hole.top + hole.height + POPOVER_GAP;
      transform = 'translate(-50%, 0)';
    }
  }

  const left = Math.min(
    Math.max(16, hole.left + hole.width / 2),
    window.innerWidth - 16,
  );

  return { top, left, transform };
}
