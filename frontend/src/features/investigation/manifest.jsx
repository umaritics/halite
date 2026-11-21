import { Navigate } from 'react-router-dom';
import { MagnifyingGlassIcon } from '@heroicons/react/24/outline';
import InvestigationsPage from './InvestigationsPage';
import InvestigationWorkspace from './InvestigationWorkspace';
import QuickDiagnose from './QuickDiagnose';
import ResearchPage from './ResearchPage';

export const routes = [
  { path: '/app/investigations/experiments', element: <ResearchPage /> },
  { path: '/app/investigations/quick', element: <QuickDiagnose /> },
  { path: '/app/investigations', element: <InvestigationsPage /> },
  { path: '/app/investigations/:id', element: <InvestigationWorkspace /> },
  { path: '/app/diagnostics', element: <Navigate to="/app/investigations" replace /> },
];
export const nav = [{ to: '/app/investigations', label: 'Investigations', icon: MagnifyingGlassIcon, order: 30 }];
