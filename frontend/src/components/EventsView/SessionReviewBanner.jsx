import { reviewSessionMessage } from '../SessionsDashboard/sessionRiskNotice.js';
import './SessionReviewBanner.css';

export default function SessionReviewBanner({ sessionRisk }) {
  if (!sessionRisk?.should_stop) return null;

  return (
    <section className="session-review-banner" role="alert">
      <div>
        <h2>Session Stop Suggested</h2>
        <p>{reviewSessionMessage(sessionRisk)}</p>
        {sessionRisk.stop_reason && <p>{sessionRisk.stop_reason}</p>}
      </div>
    </section>
  );
}
