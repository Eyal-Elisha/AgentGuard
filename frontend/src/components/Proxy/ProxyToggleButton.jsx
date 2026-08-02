export default function ProxyToggleButton({
  isActive,
  onToggle,
  ariaLabel,
  className = '',
  isPending = false,
}) {
  return (
    <button
      type="button"
      className={`proxy-toggle ${isActive ? 'proxy-toggle--on' : 'proxy-toggle--off'} ${isPending ? 'proxy-toggle--pending' : ''} ${className}`.trim()}
      onClick={onToggle}
      disabled={isPending}
      aria-pressed={isActive}
      aria-busy={isPending}
      aria-label={ariaLabel}
    >
      {isPending ? <span className="proxy-spinner" aria-hidden="true" /> : <span className="proxy-knob" />}
    </button>
  );
}
