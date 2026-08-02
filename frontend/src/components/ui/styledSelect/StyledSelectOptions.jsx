export default function StyledSelectOptions({
  listId,
  options,
  value,
  ariaLabel,
  renderOption,
  onPick,
}) {
  return (
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
              onPick(opt);
            }}
          >
            {renderOption ? renderOption(opt) : opt.label}
          </button>
        );
      })}
    </div>
  );
}
