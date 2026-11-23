import { useCallback, useEffect, useRef, useState } from 'react';
import { maintenanceAPI } from '../../api/client';
import { describeLoadError } from '../../lib/errors';

const PAGE_SIZE = 50;
const EMPTY = { items: [], total: 0, next: null, summary: {} };

function buildParams(assetId, changed, offset) {
  const params = { limit: PAGE_SIZE, offset };
  if (assetId) params.asset_id = assetId;
  if (changed) params.component_changed = changed === 'yes';
  return params;
}

// Detected corrections with aircraft and component-change filters, plus "load more".
// A failed load more keeps the rows already shown and reports its own error.
export default function useCorrections() {
  const [assets, setAssets] = useState([]);
  const [assetId, setAssetId] = useState('');
  const [changed, setChanged] = useState('');
  const [data, setData] = useState(EMPTY);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const [moreError, setMoreError] = useState(null);
  const generation = useRef(0);

  useEffect(() => {
    maintenanceAPI.assets()
      .then(({ data: rows }) => setAssets(rows || []))
      .catch(() => {});
  }, []);

  useEffect(() => {
    generation.current += 1;
    let cancelled = false;
    setLoading(true);
    setError(null);
    setMoreError(null);
    setLoadingMore(false);
    maintenanceAPI.corrections(buildParams(assetId, changed, 0))
      .then(({ data: response }) => { if (!cancelled) setData(response); })
      .catch((err) => { if (!cancelled) setError(describeLoadError(err)); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [assetId, changed]);

  const loadMore = useCallback(async () => {
    const started = generation.current;
    setLoadingMore(true);
    setMoreError(null);
    try {
      const { data: response } = await maintenanceAPI.corrections(
        buildParams(assetId, changed, data.next)
      );
      if (started !== generation.current) return;
      setData((current) => ({ ...response, items: [...current.items, ...response.items] }));
    } catch (err) {
      if (started !== generation.current) return;
      setMoreError(describeLoadError(err));
    } finally {
      if (started === generation.current) setLoadingMore(false);
    }
  }, [assetId, changed, data.next]);

  return {
    assets,
    assetId,
    setAssetId,
    changed,
    setChanged,
    data,
    loading,
    error,
    loadMore,
    loadingMore,
    moreError,
  };
}
