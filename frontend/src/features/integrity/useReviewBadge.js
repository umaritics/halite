import { useEffect, useState } from 'react';
import { maintenanceAPI } from '../../api/client';

const POLL_INTERVAL_MS = 30000;
export const REVIEW_CHANGED_EVENT = 'halite:review-changed';

// Number of records awaiting review. Polls every 30 seconds and refetches
// whenever the window receives 'halite:review-changed'.
export default function useReviewBadge() {
  const [count, setCount] = useState(0);

  useEffect(() => {
    let cancelled = false;

    const load = () =>
      maintenanceAPI
        .reviewQueue()
        .then(({ data }) => {
          if (!cancelled) setCount(Array.isArray(data) ? data.length : 0);
        })
        .catch(() => {
          if (!cancelled) setCount(0);
        });

    load();
    const interval = setInterval(load, POLL_INTERVAL_MS);
    window.addEventListener(REVIEW_CHANGED_EVENT, load);

    return () => {
      cancelled = true;
      clearInterval(interval);
      window.removeEventListener(REVIEW_CHANGED_EVENT, load);
    };
  }, []);

  return count;
}
