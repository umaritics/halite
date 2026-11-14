import React, { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import HaliteLogo from '../components/HaliteLogo';
import BrandName from '../components/BrandName';
import { authAPI } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { formatDetail } from '../utils/diagnostics';

export default function AcceptInvite() {
  const [searchParams] = useSearchParams();
  const token = (searchParams.get('token') || '').trim();
  const navigate = useNavigate();
  const { acceptInvite } = useAuth();

  const [inviteInfo, setInviteInfo] = useState(null);
  const [loadingInvite, setLoadingInvite] = useState(Boolean(token));
  const [inviteError, setInviteError] = useState(
    token ? null : 'Invitation token is missing from the URL. Ask your administrator for a fresh link.',
  );

  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);

  useEffect(() => {
    if (!token) return undefined;
    let active = true;
    setLoadingInvite(true);
    setInviteError(null);
    authAPI
      .verifyInvite(token)
      .then(({ data }) => {
        if (!active) return;
        setInviteInfo(data);
        setFullName(data.full_name || '');
      })
      .catch((err) => {
        if (!active) return;
        setInviteError(
          formatDetail(err?.response?.data?.detail) ||
            'This invitation link is invalid, expired, or has already been used.',
        );
      })
      .finally(() => {
        if (active) setLoadingInvite(false);
      });
    return () => {
      active = false;
    };
  }, [token]);

  const hasMinLen = password.length >= 10;
  const hasLetterAndNumber = /[A-Za-z]/.test(password) && /\d/.test(password);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (submitting || !inviteInfo) return;
    if (!hasMinLen || !hasLetterAndNumber) {
      setSubmitError('Password must be at least 10 characters and include both letters and numbers.');
      return;
    }
    if (password !== confirmPassword) {
      setSubmitError('Passwords do not match.');
      return;
    }

    setSubmitting(true);
    setSubmitError(null);
    try {
      await acceptInvite({ token, password, fullName: fullName.trim() });
      navigate('/app/assets', { replace: true });
    } catch (err) {
      setSubmitError(
        formatDetail(err?.response?.data?.detail) || 'Could not activate your account. Try again.',
      );
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
        <Link to="/login" className="font-sans text-sm text-secondary hover:text-primary">
          Sign in instead
        </Link>
      </header>

      <main className="mx-auto flex w-full max-w-md flex-1 items-center px-6 py-12">
        <div className="halite-card w-full p-7 sm:p-8">
          <h1 className="font-brand text-2xl text-primary">Activate workspace account</h1>

          {loadingInvite ? (
            <p className="mt-4 font-sans text-sm text-secondary">Checking invitation…</p>
          ) : inviteError ? (
            <div className="mt-4 space-y-4">
              <div
                role="alert"
                className="rounded-md border border-red-500/30 bg-red-500/10 p-4 font-sans text-sm text-red-400"
              >
                {inviteError}
              </div>
              <Link to="/login" className="halite-btn-ghost inline-flex px-4 py-2 text-sm">
                Go to sign in
              </Link>
            </div>
          ) : (
            <>
              <div className="mt-4 rounded-lg border border-theme bg-surface p-3.5 font-sans text-xs space-y-1">
                <div className="flex justify-between">
                  <span className="text-secondary">Workspace</span>
                  <span className="text-primary font-medium">{inviteInfo.organization_name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-secondary">Invited email</span>
                  <span className="font-mono text-primary">{inviteInfo.email}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-secondary">Assigned role</span>
                  <span className="font-mono text-accent">{inviteInfo.role}</span>
                </div>
              </div>

              {submitError && (
                <div
                  role="alert"
                  className="mt-4 rounded-md border border-red-500/30 bg-red-500/10 p-3 font-sans text-sm text-red-400"
                >
                  {submitError}
                </div>
              )}

              <form onSubmit={handleSubmit} className="mt-5 space-y-4">
                <div>
                  <label htmlFor="invite-name" className="block font-sans text-sm font-medium text-primary mb-1.5">
                    Full name
                  </label>
                  <input
                    id="invite-name"
                    type="text"
                    required
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    className="halite-input"
                  />
                </div>

                <div>
                  <label htmlFor="invite-password" className="block font-sans text-sm font-medium text-primary mb-1.5">
                    Choose password
                  </label>
                  <input
                    id="invite-password"
                    type="password"
                    autoComplete="new-password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="At least 10 characters"
                    className="halite-input"
                  />
                  <ul className="mt-2 space-y-1 font-sans text-xs">
                    <li className={hasMinLen ? 'text-accent' : 'text-secondary'}>
                      {hasMinLen ? '✓' : '·'} 10 or more characters
                    </li>
                    <li className={hasLetterAndNumber ? 'text-accent' : 'text-secondary'}>
                      {hasLetterAndNumber ? '✓' : '·'} Contains at least one letter and one number
                    </li>
                  </ul>
                </div>

                <div>
                  <label htmlFor="invite-confirm" className="block font-sans text-sm font-medium text-primary mb-1.5">
                    Confirm password
                  </label>
                  <input
                    id="invite-confirm"
                    type="password"
                    autoComplete="new-password"
                    required
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="halite-input"
                  />
                </div>

                <button
                  type="submit"
                  disabled={submitting}
                  className="halite-btn-primary w-full py-2.5 text-sm font-semibold disabled:opacity-60"
                >
                  {submitting ? 'Activating account…' : 'Activate account and open workspace'}
                </button>
              </form>
            </>
          )}
        </div>
      </main>
    </div>
  );
}
