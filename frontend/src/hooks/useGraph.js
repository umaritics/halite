import { useCallback, useEffect, useState } from 'react';
import { graphAPI } from '../api/client';
import { describeLoadError } from '../utils/loadError';

// `limit` is the most nodes the backend may return. The backend default is 200, which is only a
// slice of the maintenance graph (about 2,200 nodes), so the caller passes an explicit limit.
export function useGraph(limit) {
  const [data, setData] = useState({ nodes: [], edges: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchGraph = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data: graphData } = await graphAPI.overview(limit);
      setData({ nodes: graphData?.nodes ?? [], edges: graphData?.edges ?? [] });
    } catch (err) {
      console.error(err);
      setError(describeLoadError(err).message);
    } finally {
      setLoading(false);
    }
  }, [limit]);

  useEffect(() => {
    fetchGraph();
  }, [fetchGraph]);

  return { data, loading, error, refetch: fetchGraph };
}
