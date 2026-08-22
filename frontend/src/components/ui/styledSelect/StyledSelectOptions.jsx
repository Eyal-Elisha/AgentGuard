export default function StyledSelectOptions({
  listId,
  options,
  value,
  multiple = false,
  selectedValues = [],
  ariaLabel,
  renderOption,
  onPick,
}) {
  return (
    <div
      id={listId}
      className="styled-select-options"
      role="listbox"
      aria-label={ariaLabel}
      aria-multiselectable={multiple || undefined}
    >
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

        const isActive = multiple ? selectedValues.includes(opt.value) : opt.value === value;
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
              multiple ? 'styled-select-option--checkable' : '',
            ].filter(Boolean).join(' ')}
            onMouseDown={(e) => {
              e.preventDefault();
              onPick(opt);
            }}
          >
            {multiple && (
              <span className="styled-select-check" aria-hidden="true">
                {isActive ? (
                  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="m3.5 8.5 3 3 6-7" />
                  </svg>
                ) : null}
              </span>
            )}
            {renderOption ? renderOption(opt) : opt.label}
          </button>
        );
      })}
    </div>
  );
}
