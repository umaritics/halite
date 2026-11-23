import { Navigate, Route, Routes, useLocation } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import ProtectedRoute from './components/ProtectedRoute';
import Landing from './pages/Landing';
import Login from './pages/Login';
import AcceptInvite from './pages/AcceptInvite';
import { ErrorBoundary } from './components/ui';
import { featureRoutes } from './app/registry';
import { useTheme } from './context/ThemeContext';

const HOME = '/app/home';

// Software-domain URLs from the original prototype. The pages still exist in the
// repository but are not part of the Mid-I product, so old bookmarks and deep links
// land on the maintenance workspace instead of exposing them.
const LEGACY_SOFTWARE_PATHS = ['chat', 'decisions', 'ingest', 'alerts'];

function AppShell() {
  const { isDark } = useTheme();
  const { pathname } = useLocation();

  return (
    <div className={`flex h-screen overflow-hidden bg-page ${isDark ? 'text-[#F5F5F5]' : 'text-[#0A0A0A]'}`}>
      <Sidebar />
      <main className="relative min-w-0 flex-1 overflow-hidden">
        <ErrorBoundary resetKey={pathname}>
          <Routes>
            <Route index element={<Navigate to={HOME} replace />} />
            {featureRoutes.map(({ path, element, roles }) => (
              <Route key={path} path={path.replace(/^\/app\//, '')} element={
                roles?.length ? <ProtectedRoute roles={roles}>{element}</ProtectedRoute> : element
              } />
            ))}
            {LEGACY_SOFTWARE_PATHS.map((path) => (
              <Route key={path} path={path} element={<Navigate to={HOME} replace />} />
            ))}
            <Route path="*" element={<Navigate to={HOME} replace />} />
          </Routes>
        </ErrorBoundary>
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
            <AppShell />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}
