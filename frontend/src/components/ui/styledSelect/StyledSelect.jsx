import { useId, useMemo, useRef, useState } from 'react';
import '../StyledSelect.css';
import ChevronIcon from './ChevronIcon.jsx';
import StyledSelectOptions from './StyledSelectOptions.jsx';
import { useSelectDismiss } from './useSelectDismiss.js';

/** @typedef {{ value: string, label: string, disabled?: boolean, divider?: boolean }} StyledSelectOption */

/**
 * Single-select by default. With `multiple`, `value` is an array of values and
 * `onChange` receives the next array; the list stays open while picking, since
 * choosing several things one at a time is the point.
 */
export default function StyledSelect({
  value,
  onChange,
  options,
  multiple = false,
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

  const selectedValues = useMemo(
    () => (multiple ? (Array.isArray(value) ? value : []) : []),
    [multiple, value],
  );

  const selected = useMemo(
    () => (multiple ? null : options.find((o) => !o.divider && o.value === value)),
    [multiple, options, value],
  );

  useSelectDismiss(open, setOpen, rootRef);

  function toggle() {
    if (disabled) return;
    setOpen((o) => !o);
  }

  function pick(opt) {
    if (opt.disabled || opt.divider) return;
    if (multiple) {
      const next = selectedValues.includes(opt.value)
        ? selectedValues.filter((v) => v !== opt.value)
        : options.filter((o) => !o.divider)
          .map((o) => o.value)
          .filter((v) => v === opt.value || selectedValues.includes(v)); // keep catalogue order
      onChange(next);
      return;
    }
    onChange(opt.value);
    setOpen(false);
  }

  const display = renderValue
    ? renderValue(multiple ? selectedValues : selected, value)
    : multiple
      ? selectedValues.join(', ')
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
          multiple={multiple}
          selectedValues={selectedValues}
          ariaLabel={ariaLabel}
          renderOption={renderOption}
          onPick={pick}
        />
      )}
    </div>
  );
}
