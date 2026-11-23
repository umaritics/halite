import { useCallback, useEffect, useState } from 'react';
import { maintenanceAPI } from '../../api/client';
import { dateValue } from '../../utils/format';
import { describeLoadError } from '../../lib/errors';

const CONFLICT_LABELS = ['contradicts', 'partial_supersedes'];

// Conflicts first, then newest first.
function sortQueue(rows) {
  return [...rows].sort((a, b) => {
    const aConflict = CONFLICT_LABELS.includes(a.classification_label);
    const bConflict = CONFLICT_LABELS.includes(b.classification_label);
    if (aConflict && !bConflict) return -1;
    if (!aConflict && bConflict) return 1;
    return dateValue(b.occurred_at) - dateValue(a.occurred_at);
  });
}

export default function useReviewQueue() {
  const [queue, setQueue] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [index, setIndex] = useState(0);

  const reload = useCallback(() => {
    setLoading(true);
    setError(null);
    return maintenanceAPI.reviewQueue()
      .then((res) => {
        const rows = Array.isArray(res.data) ? res.data : [];
        setQueue(sortQueue(rows));
        setIndex(0);
      })
      .catch((err) => {
        console.error(err);
        setError(describeLoadError(err));
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  // Keeps the position valid after a record leaves the queue.
  const currentIndex = Math.min(index, Math.max(0, queue.length - 1));

  const remove = useCallback((recordId) => {
    setQueue((current) => current.filter((row) => row.record_id !== recordId));
  }, []);

  const prev = useCallback(() => setIndex(Math.max(0, currentIndex - 1)), [currentIndex]);

  const next = useCallback(
    () => setIndex(Math.min(queue.length - 1, currentIndex + 1)),
    [currentIndex, queue.length]
  );

  return {
    queue,
    loading,
    error,
    reload,
    remove,
    currentIndex,
    activeRecord: queue[currentIndex],
    prev,
    next,
  };
}
