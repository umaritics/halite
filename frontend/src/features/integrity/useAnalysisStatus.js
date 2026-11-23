import { useEffect, useState } from 'react';
import { maintenanceAPI } from '../../api/client';

// Counts used to explain an empty queue. null until loaded, or when it fails.
export default function useAnalysisStatus() {
  const [status, setStatus] = useState(null);

  useEffect(() => {
    maintenanceAPI.analysisStatus()
      .then(({ data }) => setStatus(data))
      .catch(() => setStatus(null));
  }, []);

  return status;
}
