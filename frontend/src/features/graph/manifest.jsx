import { lazy, Suspense } from 'react';
import { CircleStackIcon } from '@heroicons/react/24/outline';
import { Skeleton } from '../../components/ui';

// three.js and react-force-graph-3d are large; load them only when the graph page opens.
const Graph = lazy(() => import('./Graph'));

export const routes = [
  {
    path: '/app/graph',
    element: (
      <Suspense fallback={<Skeleton variant="card" lines={6} className="p-6" />}>
        <Graph />
      </Suspense>
    ),
  },
];

export const nav = [
  { to: '/app/graph', label: 'Knowledge Graph', icon: CircleStackIcon, order: 60 },
];
