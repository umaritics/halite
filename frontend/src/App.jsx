import { useEffect, useState } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import ProtectedRoute from './components/ProtectedRoute';
import Graph from './pages/Graph';
import Settings from './pages/Settings';
import Landing from './pages/Landing';
import Login from './pages/Login';
import AcceptInvite from './pages/AcceptInvite';
import TeamAccess from './pages/TeamAccess';
import Assets from './pages/Assets';
import AssetHistory from './pages/AssetHistory';
import ServiceRecords from './pages/ServiceRecords';
import ReviewQueue from './pages/ReviewQueue';
import MaintenanceIngest from './pages/MaintenanceIngest';
import { featureRoutes } from './app/registry';
import { maintenanceAPI } from './api/client';
import { useTheme } from './context/ThemeContext';
import { DomainProvider } from './context/DomainContext';

const HOME = '/app/home';

// Software-domain URLs from the original prototype. The pages still exist in the
// repository but are not part of the Mid-I product, so old bookmarks and deep links
// land on the maintenance workspace instead of exposing them.
const LEGACY_SOFTWARE_PATHS = ['chat', 'decisions', 'ingest', 'alerts'];

function AppShell() {
  const [reviewCount, setReviewCount] = useState(0);
  const { isDark } = useTheme();

  useEffect(() => {
    const load = () =>
      maintenanceAPI
        .reviewQueue()
        .then(({ data }) => setReviewCount(Array.isArray(data) ? data.length : 0))
        .catch(() => setReviewCount(0));
    load();
    const interval = setInterval(load, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className={`flex h-screen overflow-hidden bg-page ${isDark ? 'text-[#F5F5F5]' : 'text-[#0A0A0A]'}`}>
      <Sidebar reviewCount={reviewCount} />
      <main className="relative min-w-0 flex-1 overflow-hidden">
        <Routes>
          <Route index element={<Navigate to={HOME} replace />} />
          {featureRoutes.map(({ path, element, roles }) => (
            <Route key={path} path={path.replace(/^\/app\//, '')} element={
              roles?.length ? <ProtectedRoute roles={roles}>{element}</ProtectedRoute> : element
            } />
          ))}
          <Route path="assets" element={<Assets />} />
          <Route path="asset-history/:assetId" element={<AssetHistory />} />
          <Route path="records" element={<ServiceRecords />} />
          <Route path="review-queue" element={<ReviewQueue />} />
          <Route path="maintenance-ingest" element={<MaintenanceIngest />} />
          <Route path="graph" element={<Graph />} />
          <Route
            path="team"
            element={
              <ProtectedRoute roles={['admin']}>
                <TeamAccess />
              </ProtectedRoute>
            }
          />
          <Route path="settings" element={<Settings />} />
          {LEGACY_SOFTWARE_PATHS.map((path) => (
            <Route key={path} path={path} element={<Navigate to={HOME} replace />} />
          ))}
          <Route path="*" element={<Navigate to={HOME} replace />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/accept-invite" element={<AcceptInvite />} />
      <Route
        path="/app/*"
        element={
          <ProtectedRoute>
            <DomainProvider>
              <AppShell />
            </DomainProvider>
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}
