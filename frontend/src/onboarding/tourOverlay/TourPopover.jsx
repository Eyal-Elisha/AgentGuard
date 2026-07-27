export default function TourPopover({
  dialogRef,
  step,
  stepIndex,
  stepsLength,
  isFirst,
  isLast,
  hole,
  popoverStyle,
  onSkip,
  onBack,
  onNext,
}) {
  return (
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
        {stepIndex + 1} of {stepsLength}
      </p>
      <h2 id="tour-popover-title" className="tour-popover-title">{step.title}</h2>
      <p className="tour-popover-body">{step.body}</p>
      <div className="tour-popover-actions">
        {!isLast ? (
          <button type="button" className="tour-popover-skip" onClick={onSkip}>
            Skip tour
          </button>
        ) : (
          <span className="tour-popover-skip-spacer" aria-hidden="true" />
        )}
        <div className="tour-popover-nav">
          <button
            type="button"
            className="tour-popover-btn tour-popover-btn--ghost"
            onClick={onBack}
            disabled={isFirst}
          >
            Back
          </button>
          <button type="button" className="tour-popover-btn tour-popover-btn--primary" onClick={onNext}>
            {isLast ? 'Finish' : 'Next'}
          </button>
        </div>
      </div>
    </div>
  );
}
