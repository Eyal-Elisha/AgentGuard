import { useId, useMemo, useRef, useState } from 'react';
import '../StyledSelect.css';
import ChevronIcon from './ChevronIcon.jsx';
import StyledSelectOptions from './StyledSelectOptions.jsx';
import { useSelectDismiss } from './useSelectDismiss.js';

/** @typedef {{ value: string, label: string, disabled?: boolean, divider?: boolean }} StyledSelectOption */

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

  useSelectDismiss(open, setOpen, rootRef);

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
        <StyledSelectOptions
          listId={listId}
          options={options}
          value={value}
          ariaLabel={ariaLabel}
          renderOption={renderOption}
          onPick={pick}
        />
      )}
    </div>
  );
}
