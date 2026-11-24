import { useEffect, useState } from 'react';
import { maintenanceAPI } from '../../api/client';
import { formatDetail } from '../../lib/errors';
import { REVIEW_CHANGED_EVENT } from './useReviewBadge';

const TOAST_MS = 3000;

// Accept/Reject change the record's status in the graph. The UI only reflects a
// change after the server confirms it; on failure the record stays in the queue.
export default function useReviewDecision(record, onResolved) {
  const [note, setNote] = useState('');
  const [error, setError] = useState(null);
  const [pending, setPending] = useState(null);
  const [toast, setToast] = useState(null);
  const recordId = record?.record_id;

  useEffect(() => {
    setNote('');
    setError(null);
  }, [recordId]);

  useEffect(() => {
    if (!toast) return undefined;
    const timer = setTimeout(() => setToast(null), TOAST_MS);
    return () => clearTimeout(timer);
  }, [toast]);

  const submit = async (action) => {
    if (!record || pending) return;
    if (action === 'reject' && !note.trim()) {
      setError('A note is required to reject a record.');
      return;
    }

    setPending(action);
    setError(null);
    try {
      const send = action === 'accept' ? maintenanceAPI.accept : maintenanceAPI.reject;
      await send(record.record_id, note);
      onResolved(record.record_id);
      setToast(`${action === 'accept' ? 'Accepted' : 'Rejected'} record ${record.record_id}`);
      window.dispatchEvent(new Event(REVIEW_CHANGED_EVENT));
    } catch (err) {
      console.error(err);
      setError(
        formatDetail(err.response?.data?.detail) ||
          `Could not ${action} this record. It is still in the queue; nothing was changed.`
      );
    } finally {
      setPending(null);
    }
  };

  return { note, setNote, error, pending, toast, submit };
}
