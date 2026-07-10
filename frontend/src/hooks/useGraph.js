import { useCallback, useEffect, useState } from 'react';
import { graphAPI } from '../api/client';

export function useGraph() {
  const [data, setData] = useState({ nodes: [], edges: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchGraph = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data: graphData } = await graphAPI.overview();
      setData(graphData);
    } catch (err) {
      setError(err.message || 'Failed to load graph');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchGraph();
  }, [fetchGraph]);

  return { data, loading, error, refetch: fetchGraph };
}
