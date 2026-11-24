import { useEffect, useState } from 'react';
import { maintenanceAPI } from '../../api/client';
import { describeLoadError } from '../../lib/errors';

// Only called when neither the record nor the queue row carries history_size.
// The history endpoint wants the aircraft UUID, so the tail is resolved first. If it
// cannot be resolved, the count is simply not shown.
async function lookUpHistoryCount(record, whenLoaded) {
  const tail = record.asset_key || record.tail_number || record.asset_id;
  const idByTail = await whenLoaded();
  const assetUuid = idByTail[tail];
  if (!assetUuid) return null;
  try {
    const res = await maintenanceAPI.assetHistory(assetUuid);
    return res.data?.count ?? null;
  } catch {
    return null;
  }
}

// Loads the finding for the active record. Never leaves the previous record's
// finding on screen while (or after) loading the next one.
export default function useRecordDetails(record, whenLoaded) {
  const [details, setDetails] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [historyCount, setHistoryCount] = useState(null);
  const [nonce, setNonce] = useState(0);
  const recordId = record?.record_id;

  useEffect(() => {
    setDetails(null);
    setError(null);
    setHistoryCount(null);
    if (!record) {
      setLoading(false);
      return undefined;
    }

    let cancelled = false;
    setLoading(true);

    maintenanceAPI.getRecord(record.record_id)
      .then(async (res) => {
        let count = res.data?.history_size ?? record.history_size;
        if (count === undefined || count === null) {
          count = await lookUpHistoryCount(record, whenLoaded);
        }
        if (cancelled) return;
        setDetails(res.data);
        setHistoryCount(count);
      })
      .catch((err) => {
        if (cancelled) return;
        console.error(err);
        setError(describeLoadError(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [recordId, nonce]);

  const retry = () => setNonce((n) => n + 1);

  return { details, error, loading, historyCount, retry };
}
