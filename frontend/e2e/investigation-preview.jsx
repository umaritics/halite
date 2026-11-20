// Development-only integration harness while shared app-shell handoff is pending.
// HashRouter keeps reloads inside this harness; production uses BrowserRouter.
import React from 'react';
import ReactDOM from 'react-dom/client';
import { HashRouter, Link, Navigate, Route, Routes, useNavigate } from 'react-router-dom';
import { AuthProvider, useAuth } from '../src/context/AuthContext';
import { ThemeProvider, useTheme } from '../src/context/ThemeContext';
import ProtectedRoute from '../src/components/ProtectedRoute';
import Login from '../src/pages/Login';
import { routes as investigationRoutes } from '../src/features/investigation/manifest';
import { routes as homeRoutes } from '../src/features/home/manifest';
import '../src/index.css';

function Preview() {
  const { isDark, toggleTheme } = useTheme();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  return <div className="flex h-screen flex-col overflow-hidden bg-page text-primary">
    <div className="flex items-center justify-between border-b border-theme px-5 py-2 text-xs text-secondary">
      <span>Investigation integration preview</span><div className="flex items-center gap-4">{user && <><Link to="/app/home">Home</Link><Link to="/app/investigations">Investigations</Link><button type="button" onClick={async () => { await logout(); navigate('/login'); }}>Sign out</button></>}<button onClick={toggleTheme} type="button" className="halite-btn-outline">{isDark ? 'Light theme' : 'Dark theme'}</button></div>
    </div>
    <main className="min-h-0 flex-1 overflow-hidden"><Routes>
      <Route path="/login" element={<Login />} />
      {[...homeRoutes, ...investigationRoutes].map(route => <Route key={route.path} path={route.path} element={<ProtectedRoute>{route.element}</ProtectedRoute>} />)}
      <Route path="/app/assets" element={<Navigate to="/app/home" replace />} />
      <Route path="*" element={<Navigate to="/app/home" replace />} />
    </Routes></main>
  </div>;
}
ReactDOM.createRoot(document.getElementById('root')).render(<ThemeProvider><AuthProvider><HashRouter><Preview /></HashRouter></AuthProvider></ThemeProvider>);
