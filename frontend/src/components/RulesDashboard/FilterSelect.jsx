export default function FilterSelect({ label, value, onChange, options, disabled, allLabel = "All" }) {
  return (
    <label className="rules-filter-field">
      <span className="rules-filter-label">{label}</span>
      <select
        className="rules-filter-select"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
      >
        <option value="">{allLabel}</option>
        {options.map((opt) => {
          const val = typeof opt === 'object' ? opt.value : opt;
          const label = typeof opt === 'object' ? opt.label : opt;
          return (
            <option key={val} value={val}>
              {label}
            </option>
          );
        })}
      </select>
    </label>
  );
}
