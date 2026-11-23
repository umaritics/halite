import { DocumentArrowUpIcon } from '@heroicons/react/24/outline';
import MaintenanceIngest from './MaintenanceIngest';

export const routes = [{ path: '/app/maintenance-ingest', element: <MaintenanceIngest /> }];

export const nav = [
  { to: '/app/maintenance-ingest', label: 'Ingest', icon: DocumentArrowUpIcon, order: 50 },
];
