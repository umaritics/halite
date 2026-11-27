import React from 'react';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import TeamAccess from '../features/admin/TeamAccess';
import * as client from '../api/client';

vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({ user: { id: 'u-admin', role: 'admin' } }),
}));

vi.mock('../api/client', () => ({
  adminAPI: {
    listUsers: vi.fn(),
    updateUser: vi.fn(),
    listInvites: vi.fn(),
    createInvite: vi.fn(),
    revokeInvite: vi.fn(),
    auditEvents: vi.fn(),
  },
}));

const users = [
  { id: 'u-admin', email: 'admin@halite.pk', full_name: 'Admin', role: 'admin', is_active: true },
  { id: 'u-tech', email: 'tech@halite.pk', full_name: 'Tech', role: 'technician', is_active: true },
];

const invites = [
  { id: 'inv-1', email: 'new@halite.pk', full_name: 'New Person', role: 'technician' },
];

const auditEvent = {
  id: 'ev-1',
  action: 'auth.login',
  actor_email: 'admin@halite.pk',
  created_at: '2026-11-14T17:45:00Z',
};

describe('TeamAccess confirmations and audit states', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    client.adminAPI.listUsers.mockResolvedValue({ data: users });
    client.adminAPI.listInvites.mockResolvedValue({ data: invites });
    client.adminAPI.auditEvents.mockResolvedValue({ data: { items: [auditEvent] } });
    client.adminAPI.updateUser.mockResolvedValue({ data: {} });
    client.adminAPI.revokeInvite.mockResolvedValue({ data: {} });
  });

  it('asks before changing a role and only then calls the API', async () => {
    render(<TeamAccess />);
    const select = await screen.findByLabelText('Role for tech@halite.pk');

    fireEvent.change(select, { target: { value: 'supervisor' } });
    expect(client.adminAPI.updateUser).not.toHaveBeenCalled();

    const dialog = await screen.findByRole('dialog');
    fireEvent.click(within(dialog).getByRole('button', { name: 'Change role' }));

    await waitFor(() =>
      expect(client.adminAPI.updateUser).toHaveBeenCalledWith('u-tech', { role: 'supervisor' }),
    );
  });

  it('does not change the role when the dialog is cancelled', async () => {
    render(<TeamAccess />);
    const select = await screen.findByLabelText('Role for tech@halite.pk');

    fireEvent.change(select, { target: { value: 'admin' } });
    fireEvent.click(within(await screen.findByRole('dialog')).getByRole('button', { name: 'Cancel' }));

    expect(client.adminAPI.updateUser).not.toHaveBeenCalled();
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  it('asks before deactivating a user', async () => {
    render(<TeamAccess />);
    const buttons = await screen.findAllByRole('button', { name: 'Deactivate' });

    fireEvent.click(buttons[1]);
    expect(client.adminAPI.updateUser).not.toHaveBeenCalled();

    const dialog = await screen.findByRole('dialog');
    fireEvent.click(within(dialog).getByRole('button', { name: 'Deactivate' }));

    await waitFor(() =>
      expect(client.adminAPI.updateUser).toHaveBeenCalledWith('u-tech', { is_active: false }),
    );
  });

  it('asks before revoking an invitation', async () => {
    render(<TeamAccess />);
    fireEvent.click(await screen.findByRole('button', { name: 'Revoke' }));
    expect(client.adminAPI.revokeInvite).not.toHaveBeenCalled();

    const dialog = await screen.findByRole('dialog');
    fireEvent.click(within(dialog).getByRole('button', { name: 'Revoke invitation' }));

    await waitFor(() => expect(client.adminAPI.revokeInvite).toHaveBeenCalledWith('inv-1'));
  });

  it('shows an error with retry, not an empty log, when the audit request fails', async () => {
    client.adminAPI.auditEvents.mockRejectedValueOnce({ code: 'ERR_NETWORK' });
    render(<TeamAccess />);

    expect(await screen.findByRole('button', { name: 'Try again' })).toBeInTheDocument();
    expect(screen.queryByText(/no audit events recorded yet/i)).toBeNull();
    expect(screen.getByText('tech@halite.pk')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
    expect(await screen.findByText('auth.login')).toBeInTheDocument();
    expect(client.adminAPI.auditEvents).toHaveBeenCalledTimes(2);
  });

  it('shows audit times with the time of day', async () => {
    render(<TeamAccess />);
    const cell = (await screen.findByText('auth.login')).closest('tr').querySelector('td');
    expect(cell.textContent).toBe(new Date(auditEvent.created_at).toLocaleString());
  });
});
