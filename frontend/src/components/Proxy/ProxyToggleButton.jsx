export default function ProxyToggleButton({
  isActive,
  onToggle,
  ariaLabel,
  className = '',
}) {
  return (
    <button
      type="button"
      className={`proxy-toggle ${isActive ? 'proxy-toggle--on' : 'proxy-toggle--off'} ${className}`.trim()}
      onClick={onToggle}
      aria-pressed={isActive}
      aria-label={ariaLabel}
    >
      <span className="proxy-knob" />
    </button>
  );
}
