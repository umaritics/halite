import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AuthProvider, useAuth } from '../context/AuthContext';
import { ThemeProvider } from '../context/ThemeContext';
import ProtectedRoute from '../components/ProtectedRoute';
import Login from '../features/auth/Login';
import AcceptInvite from '../features/auth/AcceptInvite';
import TeamAccess from '../features/admin/TeamAccess';
import ReviewQueue from '../features/integrity/ReviewQueue';
import * as client from '../api/client';

vi.mock('../api/client', async () => {
  const actual = await vi.importActual('../api/client');
  return {
    ...actual,
    authAPI: {
      login: vi.fn(),
      refresh: vi.fn(),
      logout: vi.fn(),
      me: vi.fn(),
      changePassword: vi.fn(),
      verifyInvite: vi.fn(),
      acceptInvite: vi.fn(),
    },
    adminAPI: {
      listUsers: vi.fn(),
      updateUser: vi.fn(),
      listInvites: vi.fn(),
      createInvite: vi.fn(),
      revokeInvite: vi.fn(),
      auditEvents: vi.fn(),
    },
    maintenanceAPI: {
      ...actual.maintenanceAPI,
      assets: vi.fn(),
      reviewQueue: vi.fn(),
      getRecord: vi.fn(),
      assetHistory: vi.fn(),
      accept: vi.fn(),
      reject: vi.fn(),
      analysisStatus: vi.fn(),
      corrections: vi.fn(),
    },
  };
});

function renderAuthApp(initialEntries = ['/app/assets']) {
  return render(
    <ThemeProvider>
      <AuthProvider>
        <MemoryRouter initialEntries={initialEntries}>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/accept-invite" element={<AcceptInvite />} />
            <Route path="/app/home" element={<ProtectedRoute><div>Protected Home Workspace</div></ProtectedRoute>} />
            <Route
              path="/app/assets"
              element={
                <ProtectedRoute>
                  <div>Protected Assets Workspace</div>
                </ProtectedRoute>
              }
            />
            <Route
              path="/app/review-queue"
              element={
                <ProtectedRoute>
                  <ReviewQueue />
                </ProtectedRoute>
              }
            />
            <Route
              path="/app/team"
              element={
                <ProtectedRoute roles={['admin']}>
                  <TeamAccess />
                </ProtectedRoute>
              }
            />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    </ThemeProvider>,
  );
}

describe('Website authentication, invite activation & RBAC', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    window.sessionStorage.clear();
    window.localStorage.clear();
  });

  it('redirects unauthenticated visitors to /login and routes back after sign-in', async () => {
    client.authAPI.refresh.mockRejectedValueOnce({ response: { status: 401 } });
    client.authAPI.login.mockResolvedValueOnce({
      data: {
        access_token: 'jwt-access-1',
        refresh_token: 'refresh-1',
        user: {
          id: 'u1',
          email: 'tech@halite.pk',
          full_name: 'Shahmeer Tech',
          role: 'technician',
        },
      },
    });

    renderAuthApp(['/app/assets']);

    expect(await screen.findByRole('heading', { name: /sign in to workspace/i })).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/work email/i), {
      target: { value: 'tech@halite.pk' },
    });
    fireEvent.change(screen.getByLabelText(/^password$/i), {
      target: { value: 'StrongTechPass2026' },
    });
    fireEvent.click(screen.getByRole('button', { name: /^sign in$/i }));

    expect(await screen.findByText('Protected Assets Workspace')).toBeInTheDocument();
    expect(client.authAPI.login).toHaveBeenCalledWith('tech@halite.pk', 'StrongTechPass2026');
  });

  it('verifies an invitation token and activates the account', async () => {
    client.authAPI.refresh.mockRejectedValueOnce({ response: { status: 401 } });
    client.authAPI.verifyInvite.mockResolvedValueOnce({
      data: {
        email: 'usman@halite.pk',
        full_name: 'Muhammad Usman',
        role: 'supervisor',
        organization_name: 'Halite Maintenance Operations',
      },
    });
    client.authAPI.acceptInvite.mockResolvedValueOnce({
      data: {
        access_token: 'jwt-sup',
        refresh_token: 'refresh-sup',
        user: {
          id: 'u2',
          email: 'usman@halite.pk',
          full_name: 'Muhammad Usman',
          role: 'supervisor',
        },
      },
    });

    renderAuthApp(['/accept-invite?token=invite-token-valid-123456']);

    expect(await screen.findByText('usman@halite.pk')).toBeInTheDocument();
    expect(screen.getByText('supervisor')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/choose password/i), {
      target: { value: 'SupervisorPass2026' },
    });
    fireEvent.change(screen.getByLabelText(/confirm password/i), {
      target: { value: 'SupervisorPass2026' },
    });
    fireEvent.click(screen.getByRole('button', { name: /activate account and open workspace/i }));

    expect(await screen.findByText('Protected Home Workspace')).toBeInTheDocument();
    expect(client.authAPI.acceptInvite).toHaveBeenCalledWith({
      token: 'invite-token-valid-123456',
      password: 'SupervisorPass2026',
      fullName: 'Muhammad Usman',
    });
  });

  it('hides Accept/Reject actions for technicians in ReviewQueue and blocks /app/team', async () => {
    client.authAPI.refresh.mockResolvedValueOnce({
      data: {
        access_token: 'jwt-tech',
        refresh_token: 'refresh-tech',
        user: {
          id: 'u-tech',
          email: 'tech@halite.pk',
          full_name: 'Line Tech',
          role: 'technician',
        },
      },
    });
    client.maintenanceAPI.analysisStatus.mockResolvedValue({ data: { total: 1 } });
    client.maintenanceAPI.assets.mockResolvedValue({ data: [] });
    client.maintenanceAPI.assetHistory.mockResolvedValue({ data: { count: 1 } });
    client.maintenanceAPI.reviewQueue.mockResolvedValue({
      data: [
        {
          record_id: 'REC-1',
          asset_key: 'N813SK',
          occurred_at: '2025-02-01',
          part_name: 'PUMP',
          text: 'Pump leak',
        },
      ],
    });
    client.maintenanceAPI.getRecord.mockResolvedValue({
      data: {
        record_id: 'REC-1',
        candidates_considered: 2,
        confidence: 0.4,
        classification: { label: 'supersedes', rationale: 'Updated report' },
        best_prior: null,
      },
    });

    const { unmount } = renderAuthApp(['/app/review-queue']);
    expect(
      await screen.findByText(/supervisor or administrator access is required to accept or reject/i),
    ).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^accept$/i })).not.toBeInTheDocument();
    unmount();

    client.authAPI.refresh.mockResolvedValueOnce({
      data: {
        access_token: 'jwt-tech',
        refresh_token: 'refresh-tech',
        user: {
          id: 'u-tech',
          email: 'tech@halite.pk',
          full_name: 'Line Tech',
          role: 'technician',
        },
      },
    });
    renderAuthApp(['/app/team']);
    expect(await screen.findByText(/access restricted/i)).toBeInTheDocument();
  });

  it('allows administrators to issue single-use invitations and inspect audit events', async () => {
    client.authAPI.refresh.mockResolvedValueOnce({
      data: {
        access_token: 'jwt-admin',
        refresh_token: 'refresh-admin',
        user: {
          id: 'u-admin',
          email: 'umar@halite.pk',
          full_name: 'Muhammad Umar',
          role: 'admin',
        },
      },
    });
    client.adminAPI.listUsers.mockResolvedValue({
      data: [
        {
          id: 'u-admin',
          email: 'umar@halite.pk',
          full_name: 'Muhammad Umar',
          role: 'admin',
          is_active: true,
        },
      ],
    });
    client.adminAPI.listInvites.mockResolvedValue({ data: [] });
    client.adminAPI.auditEvents.mockResolvedValue({
      data: {
        count: 1,
        items: [
          {
            id: 'ev-1',
            action: 'maintenance.review.accepted',
            actor_email: 'umar@halite.pk',
            actor_role: 'admin',
            target_type: 'service_record',
            target_id: 'SWIA2025111676447',
            ip_address: '127.0.0.1',
            created_at: '2026-11-14T17:00:00Z',
          },
        ],
      },
    });
    client.adminAPI.createInvite.mockResolvedValueOnce({
      data: {
        invite: { id: 'inv-1', email: 'new.tech@halite.pk', role: 'technician' },
        invite_token: 'tok-xyz',
        invite_path: '/accept-invite?token=tok-xyz',
      },
    });

    renderAuthApp(['/app/team']);

    expect(await screen.findByText('maintenance.review.accepted')).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Invite email'), {
      target: { value: 'new.tech@halite.pk' },
    });
    fireEvent.change(screen.getByLabelText('Invite full name'), {
      target: { value: 'New Technician' },
    });
    fireEvent.click(screen.getByRole('button', { name: /create invite/i }));

    await waitFor(() =>
      expect(client.adminAPI.createInvite).toHaveBeenCalledWith({
        email: 'new.tech@halite.pk',
        full_name: 'New Technician',
        role: 'technician',
      }),
    );
    expect(await screen.findByText(/\/accept-invite\?token=tok-xyz/)).toBeInTheDocument();
  });
});

function SessionProbe() {
  const { status, logout, login } = useAuth();
  return <><p>{status}</p><button onClick={() => logout()}>Probe logout</button><button onClick={() => login('next@example.test', 'password')}>Probe login</button></>;
}

const legacyKeys = ['halite-diagnostic-active-workspace', 'halite-diagnostic-copilot-sessions'];
function seedLegacy() { legacyKeys.forEach(key => localStorage.setItem(key, 'unowned private notes')); }
function expectLegacyCleared() { legacyKeys.forEach(key => expect(localStorage.getItem(key)).toBeNull()); }

describe('Global authentication investigation privacy boundary', () => {
  beforeEach(() => { vi.resetAllMocks(); sessionStorage.clear(); localStorage.clear(); });
  it('discards unowned records on refresh and logout even when logout fails', async () => {
    seedLegacy();
    localStorage.setItem('unrelated-preference', 'keep');
    client.authAPI.refresh.mockResolvedValue({ data: { access_token: 'jwt', refresh_token: 'refresh', user: { id: 'owner', role: 'technician' } } });
    client.authAPI.logout.mockRejectedValue(new Error('offline'));
    render(<AuthProvider><SessionProbe /></AuthProvider>);
    await screen.findByText('authenticated');
    expectLegacyCleared();
    seedLegacy();
    fireEvent.click(screen.getByRole('button', { name: 'Probe logout' }));
    await screen.findByText('unauthenticated');
    expectLegacyCleared();
    expect(sessionStorage.getItem('halite.session.refresh.v1')).toBeNull();
    expect(localStorage.getItem('unrelated-preference')).toBe('keep');
  });
  it('discards records on failed restoration and a new account login', async () => {
    seedLegacy();
    client.authAPI.refresh.mockRejectedValue(new Error('expired'));
    client.authAPI.login.mockResolvedValue({ data: { access_token: 'new-jwt', refresh_token: 'new-refresh', user: { id: 'next', role: 'technician' } } });
    render(<AuthProvider><SessionProbe /></AuthProvider>);
    await screen.findByText('unauthenticated');
    expectLegacyCleared();
    seedLegacy();
    fireEvent.click(screen.getByRole('button', { name: 'Probe login' }));
    await screen.findByText('authenticated');
    expectLegacyCleared();
  });
});
