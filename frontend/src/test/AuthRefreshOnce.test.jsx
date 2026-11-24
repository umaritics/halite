import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AuthProvider, useAuth } from '../context/AuthContext';
import * as client from '../api/client';

vi.mock('../api/client', async () => {
  const actual = await vi.importActual('../api/client');
  return {
    ...actual,
    authAPI: { ...actual.authAPI, refresh: vi.fn() },
  };
});

function Status() {
  const { status, user } = useAuth();
  return <p>{status}:{user?.email || 'none'}</p>;
}

describe('session restore', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
  });

  // Refresh tokens rotate, so a second call with the same token is rejected
  // and used to sign the user out on reload in development (StrictMode runs
  // the restore effect twice).
  it('sends one refresh request when the restore effect runs twice', async () => {
    client.authAPI.refresh.mockResolvedValue({
      data: {
        access_token: 'access-1',
        refresh_token: 'refresh-2',
        user: { email: 'tech@halite.pk', role: 'technician' },
      },
    });

    render(
      <React.StrictMode>
        <AuthProvider>
          <Status />
        </AuthProvider>
      </React.StrictMode>,
    );

    await waitFor(() => expect(screen.getByText('authenticated:tech@halite.pk')).toBeInTheDocument());
    expect(client.authAPI.refresh).toHaveBeenCalledTimes(1);
  });
});
