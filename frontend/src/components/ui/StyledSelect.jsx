import { useEffect, useId, useMemo, useRef, useState } from 'react';
import './StyledSelect.css';

function ChevronIcon() {
  return (
    <svg className="styled-select-chevron" width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
      <path d="M3 4.5L6 7.5L9 4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/**
 * @typedef {{ value: string, label: string, disabled?: boolean, divider?: boolean }} StyledSelectOption
 */

/**
 * @param {{
 *   value: string,
 *   onChange: (value: string) => void,
 *   options: StyledSelectOption[],
 *   disabled?: boolean,
 *   ariaLabel?: string,
 *   className?: string,
 *   triggerClassName?: string,
 *   renderValue?: (option: StyledSelectOption | undefined, value: string) => import('react').ReactNode,
 *   renderOption?: (option: StyledSelectOption) => import('react').ReactNode,
 * }} props
 */
export default function StyledSelect({
  value,
  onChange,
  options,
  disabled = false,
  ariaLabel,
  className = '',
  triggerClassName = '',
  renderValue,
  renderOption,
}) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef(null);
  const listId = useId();

  const selected = useMemo(
    () => options.find((o) => !o.divider && o.value === value),
    [options, value],
  );

  useEffect(() => {
    if (!open) return undefined;

    function onKey(e) {
      if (e.key === 'Escape') {
        e.preventDefault();
        setOpen(false);
      }
    }

    function onPointerDown(e) {
      if (rootRef.current && !rootRef.current.contains(e.target)) {
        setOpen(false);
      }
    }

    window.addEventListener('keydown', onKey);
    window.addEventListener('pointerdown', onPointerDown);
    return () => {
      window.removeEventListener('keydown', onKey);
      window.removeEventListener('pointerdown', onPointerDown);
    };
  }, [open]);

  function toggle() {
    if (disabled) return;
    setOpen((o) => !o);
  }

  function pick(opt) {
    if (opt.disabled || opt.divider) return;
    onChange(opt.value);
    setOpen(false);
  }

  const display = renderValue
    ? renderValue(selected, value)
    : (selected?.label ?? value);

  return (
    <div
      ref={rootRef}
      className={`styled-select${className ? ` ${className}` : ''}${disabled ? ' styled-select--disabled' : ''}`}
    >
      <button
        type="button"
        className={`styled-select-trigger${triggerClassName ? ` ${triggerClassName}` : ''}`}
        onClick={toggle}
        disabled={disabled}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={open ? listId : undefined}
        aria-label={ariaLabel}
      >
        <span className="styled-select-value">{display}</span>
        <ChevronIcon />
      </button>

      {open && (
        <div id={listId} className="styled-select-options" role="listbox" aria-label={ariaLabel}>
          {options.map((opt, index) => {
            if (opt.divider) {
              return (
                <div
                  key={`divider-${index}`}
                  className="styled-select-divider"
                  role="separator"
                />
              );
            }

            const isActive = opt.value === value;
            return (
              <button
                key={opt.value}
                type="button"
                role="option"
                aria-selected={isActive}
                disabled={opt.disabled}
                className={[
                  'styled-select-option',
                  isActive ? 'styled-select-option--active' : '',
                  opt.disabled ? 'styled-select-option--disabled' : '',
                ].filter(Boolean).join(' ')}
                onMouseDown={(e) => {
                  e.preventDefault();
                  pick(opt);
                }}
              >
                {renderOption ? renderOption(opt) : opt.label}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
