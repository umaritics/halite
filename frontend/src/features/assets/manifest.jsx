import { ClipboardDocumentListIcon, WrenchScrewdriverIcon } from '@heroicons/react/24/outline';
import Assets from './Assets';
import AssetHistory from './AssetHistory';
import ServiceRecords from './ServiceRecords';

export const routes = [
  { path: '/app/assets', element: <Assets /> },
  { path: '/app/asset-history/:assetId', element: <AssetHistory /> },
  { path: '/app/records', element: <ServiceRecords /> },
];

export const nav = [
  { to: '/app/assets', label: 'Assets', icon: WrenchScrewdriverIcon, order: 10 },
  { to: '/app/records', label: 'Service Records', icon: ClipboardDocumentListIcon, order: 20 },
];
