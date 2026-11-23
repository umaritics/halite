import { Cog6ToothIcon, UsersIcon } from '@heroicons/react/24/outline';
import TeamAccess from './TeamAccess';
import Settings from './Settings';

export const routes = [
  { path: '/app/team', element: <TeamAccess />, roles: ['admin'] },
  { path: '/app/settings', element: <Settings /> },
];

export const nav = [
  { to: '/app/team', label: 'Team & Access', icon: UsersIcon, order: 70, roles: ['admin'] },
  { to: '/app/settings', label: 'Settings', icon: Cog6ToothIcon, order: 80 },
];
