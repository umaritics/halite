import { CircleStackIcon } from '@heroicons/react/24/outline';
import Graph from '../../pages/Graph';

export const routes = [{ path: '/app/graph', element: <Graph /> }];

export const nav = [
  { to: '/app/graph', label: 'Knowledge Graph', icon: CircleStackIcon, order: 60 },
];
