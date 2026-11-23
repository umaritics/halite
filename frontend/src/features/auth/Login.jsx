import React, { useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { EyeIcon, EyeSlashIcon, MoonIcon, SunIcon } from '@heroicons/react/24/outline';
import HaliteLogo from '../../components/HaliteLogo';
import BrandName from '../../components/BrandName';
import { useAuth } from '../../context/AuthContext';
import { useTheme } from '../../context/ThemeContext';
import { formatDetail } from '../../utils/diagnostics';

function ProvenanceSchematic({ isDark }) {
  const strokeMuted = isDark ? '#2A2A2A' : '#D4D4D4';
  const fillBox = isDark ? '#0D0D0D' : '#F8F8F8';
  const textMain = isDark ? '#F5F5F5' : '#0A0A0A';
  const textSub = isDark ? '#888888' : '#555555';

  return (
    <div className="mt-8 rounded-xl border border-theme bg-surface p-5">
      <svg
        viewBox="0 0 460 124"
        className="w-full h-auto"
        role="img"
        aria-label="Chain of custody from aircraft tail number to verified reviewer decision"
      >
        {/* Connecting lines */}
        <line x1="126" y1="46" x2="174" y2="46" stroke={strokeMuted} strokeWidth="1.5" />
        <line x1="306" y1="46" x2="346" y2="46" stroke="#E8650A" strokeWidth="1.5" strokeDasharray="4 3" />
        <polygon points="172,42 179,46 172,50" fill={strokeMuted} />
        <polygon points="344,42 351,46 344,50" fill="#E8650A" />

        {/* Node 1: Asset */}
        <rect x="8" y="18" width="118" height="56" rx="8" fill={fillBox} stroke={strokeMuted} />
        <text x="20" y="40" fill={textMain} fontSize="12" fontFamily="monospace" fontWeight="600">
          N813SK
        </text>
        <text x="20" y="58" fill={textSub} fontSize="10" fontFamily="sans-serif">
          153 SDR filings
        </text>

        {/* Node 2: Cited ServiceRecord */}
        <rect x="180" y="18" width="126" height="56" rx="8" fill={fillBox} stroke={strokeMuted} />
        <text x="192" y="40" fill={textMain} fontSize="11" fontFamily="monospace" fontWeight="600">
          SWIA20251116
        </text>
        <text x="192" y="58" fill={textSub} fontSize="10" fontFamily="sans-serif">
          Graph-verified ID
        </text>

        {/* Node 3: Signed Reviewer */}
        <rect x="352" y="18" width="100" height="56" rx="8" fill={fillBox} stroke="#E8650A" strokeWidth="1.25" />
        <text x="364" y="40" fill="#E8650A" fontSize="11" fontFamily="sans-serif" fontWeight="600">
          Reviewed
        </text>
        <text x="364" y="58" fill={textSub} fontSize="10" fontFamily="sans-serif">
          Signed audit log
        </text>

        {/* Caption baseline */}
        <text x="8" y="106" fill={textSub} fontSize="10.5" fontFamily="sans-serif">
          Every diagnostic check cites a stored report ID; every conflict decision records the reviewer.
        </text>
      </svg>
    </div>
  );
}

export default function Login() {
  const { status, isAuthenticated, login } = useAuth();
  const { isDark, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const destination =
    location.state?.from?.pathname && location.state.from.pathname.startsWith('/app')
      ? `${location.state.from.pathname}${location.state.from.search || ''}${location.state.from.hash || ''}`
      : '/app/home';

  if (status === 'authenticated' && isAuthenticated) {
    return <Navigate to={destination} replace />;
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (submitting) return;
    const trimmedEmail = email.trim();
    if (!trimmedEmail || !password) {
      setError('Enter both your work email and password.');
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      await login(trimmedEmail, password);
      navigate(destination, { replace: true });
    } catch (err) {
      const httpStatus = err?.response?.status;
      const detail = formatDetail(err?.response?.data?.detail);
      if (!err?.response) {
        setError('Cannot reach the Halite authentication service. Check that the backend is online.');
      } else if (httpStatus === 429) {
        setError(detail || 'Too many failed sign-in attempts. Wait before trying again.');
      } else if (httpStatus === 403) {
        setError(detail || 'This account is inactive. Contact your workspace administrator.');
      } else {
        setError(detail || 'Invalid email or password.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-page flex flex-col">
      <header className="flex h-16 items-center justify-between border-b border-theme px-6">
        <Link to="/" className="flex items-center gap-3">
          <HaliteLogo className="h-8 w-8" />
          <BrandName className="text-xl text-accent" />
        </Link>
        <button
          type="button"
          onClick={toggleTheme}
          className="rounded-md p-2 text-secondary transition hover:text-accent"
          aria-label="Toggle theme"
        >
          {isDark ? <SunIcon className="h-5 w-5" /> : <MoonIcon className="h-5 w-5" />}
        </button>
      </header>

      <main className="mx-auto grid w-full max-w-5xl flex-1 items-center gap-12 px-6 py-12 lg:grid-cols-[1.08fr_0.92fr]">
        {/* Left: Subject-grounded operational context */}
        <section className="lg:pr-8 lg:border-r lg:border-theme">
          <h1 className="font-brand text-3xl sm:text-4xl leading-tight text-primary max-w-lg">
            Traceable maintenance history for authorised flight-line teams.
          </h1>
          <p className="mt-4 font-sans text-sm leading-relaxed text-secondary max-w-lg">
            Sign in to inspect aircraft service records, run evidence-grounded diagnostic sessions,
            and adjudicate historical report corrections with full reviewer attribution.
          </p>

          <ProvenanceSchematic isDark={isDark} />

          <dl className="mt-6 grid gap-3 sm:grid-cols-3 font-sans text-xs">
            <div className="rounded-lg border border-theme p-3">
              <dt className="font-medium text-primary">Technician</dt>
              <dd className="mt-1 text-secondary">Browse fleet history, ingest reports, and run Copilot diagnostics.</dd>
            </div>
            <div className="rounded-lg border border-theme p-3">
              <dt className="font-medium text-primary">Supervisor</dt>
              <dd className="mt-1 text-secondary">Accept or reject flagged conflicts with a signed review note.</dd>
            </div>
            <div className="rounded-lg border border-theme p-3">
              <dt className="font-medium text-primary">Administrator</dt>
              <dd className="mt-1 text-secondary">Issue single-use team invitations, manage roles, and inspect audit logs.</dd>
            </div>
          </dl>
        </section>

        {/* Right: Sign-in ledger */}
        <section className="w-full max-w-md mx-auto lg:mx-0">
          <div className="halite-card p-7 sm:p-8">
            <h2 className="font-brand text-2xl text-primary">Sign in to workspace</h2>
            <p className="mt-1.5 font-sans text-sm text-secondary">
              Use the credentials or invitation issued by your workspace administrator.
            </p>

            {error && (
              <div
                role="alert"
                className="mt-5 rounded-md border border-red-500/30 bg-red-500/10 px-4 py-3 font-sans text-sm text-red-400"
              >
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="mt-6 space-y-4" noValidate>
              <div>
                <label htmlFor="login-email" className="block font-sans text-sm font-medium text-primary mb-1.5">
                  Work email
                </label>
                <input
                  id="login-email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@organization.pk"
                  className="halite-input"
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label htmlFor="login-password" className="font-sans text-sm font-medium text-primary">
                    Password
                  </label>
                  <button
                    type="button"
                    onClick={() => setShowPassword((prev) => !prev)}
                    className="inline-flex items-center gap-1 font-sans text-xs text-secondary hover:text-primary"
                  >
                    {showPassword ? (
                      <>
                        <EyeSlashIcon className="h-3.5 w-3.5" /> Hide
                      </>
                    ) : (
                      <>
                        <EyeIcon className="h-3.5 w-3.5" /> Show
                      </>
                    )}
                  </button>
                </div>
                <input
                  id="login-password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  className="halite-input"
                />
              </div>

              <button
                type="submit"
                disabled={submitting}
                className="halite-btn-primary w-full py-2.5 text-sm font-semibold disabled:opacity-60"
              >
                {submitting ? 'Signing in…' : 'Sign in'}
              </button>
            </form>

            <div className="mt-6 border-t border-theme pt-4 font-sans text-xs text-secondary leading-relaxed">
              Registration is invite-only to protect fleet records and model capacity.
              Have an invitation token? Open your invitation link directly to set your password.
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
