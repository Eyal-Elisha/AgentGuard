import { isIsoEmpty } from './sessionUtils.js';
import './SessionStatusBadge.css';

/**
 * Displays a pill badge indicating if a session is Active or Closed.
 * A session is "active" if it has no valid end_time.
 */
export default function SessionStatusBadge({ endTime }) {
  const isClosed = !isIsoEmpty(endTime);
  return (
    <span className={`session-status-badge session-status-badge--${isClosed ? 'closed' : 'active'}`}>
      {isClosed ? 'Closed' : 'Active'}
    </span>
  );
}
