import { useEffect, useRef } from 'react';
import '../SessionsDashboard/DeleteSessionModal.css';

/**
 * Confirmation modal before deleting a domain from the blacklist.
 * Traps focus, closes on Escape, and prevents scroll on the body.
 */
export default function DeleteDomainModal({ domain, onConfirm, onCancel, isPending }) {
  const confirmRef = useRef(null);

  useEffect(() => {
    confirmRef.current?.focus();
    const onKey = (e) => { if (e.key === 'Escape') onCancel(); };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onCancel]);

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="delete-domain-title">
      <div className="modal-card">
        <h2 id="delete-domain-title" className="modal-title">Remove Domain?</h2>
        <p className="modal-body">
          Are you sure you want to remove <strong>{domain}</strong> from the custom blacklist? This will allow traffic to this domain again.
        </p>
        <div className="modal-actions">
          <button
            type="button"
            className="modal-btn modal-btn--cancel"
            onClick={onCancel}
            disabled={isPending}
          >
            Cancel
          </button>
          <button
            ref={confirmRef}
            type="button"
            className="modal-btn modal-btn--confirm"
            onClick={onConfirm}
            disabled={isPending}
            aria-busy={isPending}
          >
            {isPending ? 'Removing…' : 'Remove'}
          </button>
        </div>
      </div>
    </div>
  );
}
