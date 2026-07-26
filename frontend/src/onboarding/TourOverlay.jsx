import { useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { useTour } from './TourProvider.jsx';
import { computePopoverStyle, SPOTLIGHT_PAD } from './tourOverlay/geometry.js';
import TourPopover from './tourOverlay/TourPopover.jsx';
import TourSpotlight from './tourOverlay/TourSpotlight.jsx';
import { useTourChrome } from './tourOverlay/useTourChrome.js';
import { useTourTarget } from './tourOverlay/useTourTarget.js';
import './tourOverlay/index.css';

export default function TourOverlay() {
  const { isOpen, step, stepIndex, steps, next, back, skip } = useTour();
  const { pathname: locationPath } = useLocation();
  const dialogRef = useRef(null);
  const isLast = stepIndex >= steps.length - 1;
  const isFirst = stepIndex === 0;

  const target = useTourTarget({ isOpen, step, stepIndex, locationPath });
  useTourChrome({ isOpen, stepIndex, skip, dialogRef });

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
      <TourSpotlight hole={hole} />
      <TourPopover
        dialogRef={dialogRef}
        step={step}
        stepIndex={stepIndex}
        stepsLength={steps.length}
        isFirst={isFirst}
        isLast={isLast}
        hole={hole}
        popoverStyle={popoverStyle}
        onSkip={skip}
        onBack={back}
        onNext={next}
      />
    </div>
  );
}
