import { useEffect, useState } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Chat from './pages/Chat';
import Graph from './pages/Graph';
import Decisions from './pages/Decisions';
import Ingest from './pages/Ingest';
import Alerts from './pages/Alerts';
import Settings from './pages/Settings';
import Landing from './pages/Landing';
import Assets from './pages/Assets';
import AssetHistory from './pages/AssetHistory';
import ServiceRecords from './pages/ServiceRecords';
import ReviewQueue from './pages/ReviewQueue';
import MaintenanceIngest from './pages/MaintenanceIngest';
import Diagnostics from './pages/Diagnostics';
import { alertsAPI } from './api/client';
import { useTheme } from './context/ThemeContext';

function AppShell() {
  const [alertCount, setAlertCount] = useState(0);
  const { isDark } = useTheme();

  useEffect(() => {
    alertsAPI
      .list()
      .then(({ data }) => setAlertCount(data.length))
      .catch(() => setAlertCount(0));
    const interval = setInterval(() => {
      alertsAPI
        .list()
        .then(({ data }) => setAlertCount(data.length))
        .catch(() => {});
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className={`flex h-screen overflow-hidden bg-page ${isDark ? 'text-[#F5F5F5]' : 'text-[#0A0A0A]'}`}>
      <Sidebar alertCount={alertCount} />
      <main className="relative flex-1 overflow-hidden">
        <Routes>
          <Route index element={<Navigate to="chat" replace />} />
          <Route path="chat" element={<Chat />} />
          <Route path="graph" element={<Graph />} />
          <Route path="decisions" element={<Decisions />} />
          <Route path="ingest" element={<Ingest />} />
          <Route path="alerts" element={<Alerts />} />
          <Route path="settings" element={<Settings />} />
          <Route path="assets" element={<Assets />} />
          <Route path="asset-history/:assetId" element={<AssetHistory />} />
          <Route path="records" element={<ServiceRecords />} />
          <Route path="review-queue" element={<ReviewQueue />} />
          <Route path="maintenance-ingest" element={<MaintenanceIngest />} />
          <Route path="diagnostics" element={<Diagnostics />} />
        </Routes>
      </main>
    </div>
  );
}

import { DomainProvider } from './context/DomainContext';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/app/*" element={
        <DomainProvider>
          <AppShell />
        </DomainProvider>
      } />
    </Routes>
  );
}
