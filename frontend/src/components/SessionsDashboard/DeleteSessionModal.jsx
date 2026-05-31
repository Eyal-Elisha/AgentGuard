import { useEffect, useRef } from 'react';
import './DeleteSessionModal.css';

/**
 * Confirmation modal before deleting a session.
 * Traps focus, closes on Escape, and prevents scroll on the body.
 */
export default function DeleteSessionModal({ sessionId, onConfirm, onCancel, isPending, error }) {
  const confirmRef = useRef(null);

  useEffect(() => {
    confirmRef.current?.focus();
    const onKey = (e) => { if (e.key === 'Escape') onCancel(); };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onCancel]);

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="delete-modal-title">
      <div className="modal-card">
        <h2 id="delete-modal-title" className="modal-title">Delete Session #{sessionId}?</h2>
        <p className="modal-body">
          This will permanently delete the session and all its associated events. This action cannot be undone.
        </p>
        {error && (
          <div className="sessions-error-alert" role="alert" style={{ marginBottom: '1rem', color: 'var(--color-risk-high)', fontSize: '0.85rem' }}>
            {error}
          </div>
        )}
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
            {isPending ? 'Deleting…' : 'Delete'}
          </button>
        </div>
      </div>
    </div>
  );
}
