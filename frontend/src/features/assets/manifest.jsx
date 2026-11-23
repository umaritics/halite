import { ClipboardDocumentListIcon, WrenchScrewdriverIcon } from '@heroicons/react/24/outline';
import Assets from '../../pages/Assets';
import AssetHistory from '../../pages/AssetHistory';
import ServiceRecords from '../../pages/ServiceRecords';

export const routes = [
  { path: '/app/assets', element: <Assets /> },
  { path: '/app/asset-history/:assetId', element: <AssetHistory /> },
  { path: '/app/records', element: <ServiceRecords /> },
];

export const nav = [
  { to: '/app/assets', label: 'Assets', icon: WrenchScrewdriverIcon, order: 10 },
  { to: '/app/records', label: 'Service Records', icon: ClipboardDocumentListIcon, order: 20 },
];
