import StyledSelect from '../ui/StyledSelect.jsx';

export default function FilterSelect({
  label,
  value,
  onChange,
  options,
  disabled,
  allLabel = 'All',
  allValue = '',
}) {
  const selectOptions = [
    { value: String(allValue), label: allLabel },
    ...options.map((opt) => {
      if (typeof opt === 'object') {
        return { value: String(opt.value), label: opt.label };
      }
      return { value: String(opt), label: String(opt) };
    }),
  ];

  return (
    <label className="rules-filter-field">
      <span className="rules-filter-label">{label}</span>
      <StyledSelect
        className="styled-select--compact"
        value={String(value ?? '')}
        onChange={onChange}
        options={selectOptions}
        disabled={disabled}
        ariaLabel={label}
      />
    </label>
  );
}
