import { useCallback, useEffect, useRef, useState } from 'react';
import { maintenanceAPI } from '../../api/client';

// Maps tail number to asset UUID. whenLoaded() lets a caller wait for the list
// without re-running its own effect when the list arrives. A failed load gives an
// empty map, because links and history counts are optional extras.
export default function useAssetIds() {
  const [idByTail, setIdByTail] = useState({});
  const deferred = useRef(null);

  if (!deferred.current) {
    let resolve;
    const promise = new Promise((done) => { resolve = done; });
    deferred.current = { promise, resolve };
  }

  useEffect(() => {
    let cancelled = false;
    maintenanceAPI.assets()
      .then((res) => {
        const map = {};
        (res.data ?? []).forEach((asset) => { map[asset.tail_number] = asset.id; });
        if (!cancelled) setIdByTail(map);
        deferred.current.resolve(map);
      })
      .catch(() => deferred.current.resolve({}));
    return () => { cancelled = true; };
  }, []);

  const whenLoaded = useCallback(() => deferred.current.promise, []);

  return { idByTail, whenLoaded };
}
