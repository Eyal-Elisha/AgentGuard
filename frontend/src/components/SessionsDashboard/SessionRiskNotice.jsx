import { markReviewSessionSeen, reviewSessionMessage } from './sessionRiskNotice.js';
import './SessionRiskNotice.css';

export default function SessionRiskNotice({ session, onClose }) {
  if (!session) return null;

  function closeNotice() {
    markReviewSessionSeen(session.session_id);
    onClose();
  }

  return (
    <div className="session-risk-notice" role="alertdialog" aria-modal="false">
      <div>
        <h2>Session Stop Suggested</h2>
        <p>{reviewSessionMessage(session)}</p>
      </div>
      <button type="button" onClick={closeNotice}>
        Got it
      </button>
    </div>
  );
}
