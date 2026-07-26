import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { useTour } from './TourProvider.jsx';
import './tourOverlay/index.css';

const POPOVER_EST_HEIGHT = 200;
const POPOVER_GAP = 14;
const SPOTLIGHT_PAD = 6;
const TALL_TARGET_CAP = 120;
const TALL_TARGET_THRESHOLD = 140;

function measureTarget(selector) {
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

function computePopoverStyle(hole) {
  if (!hole) return undefined;

  const spaceBelow = window.innerHeight - (hole.top + hole.height);
  const spaceAbove = hole.top;
  let preferBelow = spaceBelow >= POPOVER_EST_HEIGHT || spaceBelow >= spaceAbove;

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

export default function TourOverlay() {
  const { isOpen, step, stepIndex, steps, next, back, skip } = useTour();
  const { pathname: locationPath } = useLocation();
  const dialogRef = useRef(null);
  const [target, setTarget] = useState(null);
  const isLast = stepIndex >= steps.length - 1;
  const isFirst = stepIndex === 0;

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

  useEffect(() => {
    if (!isOpen) return undefined;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    dialogRef.current?.focus();
    return () => { document.body.style.overflow = prev; };
  }, [isOpen, stepIndex]);

  useEffect(() => {
    if (!isOpen) return undefined;
    function onKey(e) {
      if (e.key === 'Escape') {
        e.preventDefault();
        skip();
      }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [isOpen, skip]);

  if (!isOpen || !step) return null;

  const pad = SPOTLIGHT_PAD;
  const hole = target
    ? {
        top: Math.max(8, target.top - pad),
        left: Math.max(8, target.left - pad),
        width: target.width + pad * 2,
        height: target.height + pad * 2,
        round: target.round,
      }
    : null;

  const popoverStyle = computePopoverStyle(hole);

  return (
    <div className="tour-overlay" role="presentation">
      {hole ? (
        <div
          className={`tour-spotlight${hole.round ? ' tour-spotlight--round' : ''}`}
          aria-hidden="true"
          onClick={(e) => e.stopPropagation()}
          onMouseDown={(e) => e.preventDefault()}
          style={{
            top: hole.top,
            left: hole.left,
            width: hole.width,
            height: hole.height,
          }}
        />
      ) : (
        <div className="tour-backdrop" aria-hidden="true" />
      )}
      <div
        ref={dialogRef}
        className={`tour-popover${hole ? '' : ' tour-popover--centered'}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby="tour-popover-title"
        tabIndex={-1}
        style={hole ? popoverStyle : undefined}
      >
        <p className="tour-popover-progress">
          {stepIndex + 1} of {steps.length}
        </p>
        <h2 id="tour-popover-title" className="tour-popover-title">{step.title}</h2>
        <p className="tour-popover-body">{step.body}</p>
        <div className="tour-popover-actions">
          {!isLast ? (
            <button type="button" className="tour-popover-skip" onClick={skip}>
              Skip tour
            </button>
          ) : (
            <span className="tour-popover-skip-spacer" aria-hidden="true" />
          )}
          <div className="tour-popover-nav">
            <button
              type="button"
              className="tour-popover-btn tour-popover-btn--ghost"
              onClick={back}
              disabled={isFirst}
            >
              Back
            </button>
            <button type="button" className="tour-popover-btn tour-popover-btn--primary" onClick={next}>
              {isLast ? 'Finish' : 'Next'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
