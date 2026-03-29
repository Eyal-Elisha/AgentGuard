import './ShieldIcon.css';

export default function ShieldIcon() {
  return (
    <svg
      className="logo-shield-icon"
      viewBox="0 0 24 24"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <path
        className="logo-shield-icon__outline"
        d="M12 2L4 5v6.09c0 5.05 3.41 9.76 8 10.91 4.59-1.15 8-5.86 8-10.91V5l-8-3z"
      />
      <path className="logo-shield-icon__check" d="M9 12l2 2 4-4" />
    </svg>
  );
}
