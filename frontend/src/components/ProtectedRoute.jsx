import React from 'react';
import { Link, Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import HaliteLogo from './HaliteLogo';

export default function ProtectedRoute({ children, roles }) {
  const { status, user, hasRole } = useAuth();
  const location = useLocation();

  if (status === 'loading') {
    return (
      <div className="flex min-h-screen items-center justify-center bg-page px-6">
        <div className="flex items-center gap-3 text-secondary font-sans text-sm">
          <HaliteLogo className="h-7 w-7 animate-pulse" />
          <span>Verifying workspace session…</span>
        </div>
      </div>
    );
  }

  if (status !== 'authenticated' || !user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (Array.isArray(roles) && roles.length > 0 && !hasRole(...roles)) {
    return (
      <div className="flex h-full items-center justify-center p-6">
        <div role="alert" className="halite-card max-w-md p-6">
          <h2 className="font-brand text-lg text-primary">Access restricted</h2>
          <p className="mt-2 font-sans text-sm text-secondary">
            Your account is signed in as <span className="font-mono text-primary">{user.role}</span>.
            This view requires {roles.join(' or ')} permissions.
          </p>
          <Link to="/app/assets" className="halite-btn-primary mt-5 inline-flex text-sm">
            Return to Assets
          </Link>
        </div>
      </div>
    );
  }

  return children;
}
