import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import Sidebar from '../components/Sidebar';

const state = vi.hoisted(() => ({ user: null, logout: vi.fn() }));
vi.mock('../context/ThemeContext', () => ({ useTheme: () => ({ isDark: true }) }));
vi.mock('../context/AuthContext', () => ({ useAuth: () => ({ isAuthenticated: true, user: state.user, logout: state.logout }) }));

function mount(reviewCount = 0) {
  return render(<MemoryRouter initialEntries={['/app/investigations']}>
    <Routes>
      <Route path="/app/*" element={<Sidebar reviewCount={reviewCount} />} />
      <Route path="/login" element={<h1>Signed out</h1>} />
    </Routes>
  </MemoryRouter>);
}

beforeEach(() => {
  state.user = { id: 'synthetic-owner', full_name: 'Synthetic Owner', email: 'synthetic@sessions.test', role: 'technician' };
  state.logout.mockReset().mockResolvedValue(undefined);
});

describe('Responsive investigation shell integration', () => {
  it('keeps icon navigation accessible by destination name and preserves the active route', () => {
    mount(9);
    for (const label of ['Home', 'Assets', 'Service Records', 'Investigations', 'Review Queue', 'Ingest', 'Knowledge Graph', 'Settings']) {
      expect(screen.getByRole('link', { name: label, exact: true })).toBeInTheDocument();
    }
    expect(screen.getByRole('link', { name: 'Review Queue', exact: true })).toHaveAttribute('href', '/app/review-queue');
    expect(screen.getByRole('link', { name: 'Investigations', exact: true })).toHaveAttribute('aria-current', 'page');
    expect(screen.getByLabelText('9 records awaiting review')).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Team & Access', exact: true })).not.toBeInTheDocument();
  });

  it('preserves role-scoped team navigation', () => {
    state.user.role = 'admin';
    mount();
    expect(screen.getByRole('link', { name: 'Team & Access', exact: true })).toHaveAttribute('href', '/app/team');
  });

  it('keeps the icon-only sign-out action named and waits for confirmed logout', async () => {
    let resolve;
    state.logout.mockImplementation(() => new Promise(r => { resolve = r; }));
    mount();
    fireEvent.click(screen.getByRole('button', { name: 'Sign out', exact: true }));
    expect(state.logout).toHaveBeenCalledOnce();
    expect(screen.queryByRole('heading', { name: 'Signed out' })).not.toBeInTheDocument();
    resolve();
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Signed out' })).toBeInTheDocument());
  });
});
