import { HomeIcon } from '@heroicons/react/24/outline';
import HomePage from './HomePage';

export const routes = [{ path: '/app/home', element: <HomePage /> }];
export const nav = [{ to: '/app/home', label: 'Home', icon: HomeIcon, order: 0 }];
