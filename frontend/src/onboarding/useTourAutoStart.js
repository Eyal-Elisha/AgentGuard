import { useEffect } from 'react';
import { isTourCompleted } from './tourStorage.js';

/** Auto-start the tour once for users who have not completed it. */
export function useTourAutoStart({ currentUser, userKey, startTour }) {
  useEffect(() => {
    if (!currentUser) return undefined;
    if (isTourCompleted(userKey)) return undefined;
    const t = window.setTimeout(() => {
      startTour();
    }, 400);
    return () => window.clearTimeout(t);
  }, [currentUser, userKey]); // eslint-disable-line react-hooks/exhaustive-deps -- auto-start once per user when incomplete
}
