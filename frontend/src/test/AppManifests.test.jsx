import React from 'react';
import { act, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import App from '../App';
import Sidebar from '../components/Sidebar';
import { ThemeProvider } from '../context/ThemeContext';
import { featureNav, featureRoutes } from '../app/registry';

const auth = vi.hoisted(() => ({
  status: 'authenticated',
  isAuthenticated: true,
  user: { id: 'u1', role: 'technician', full_name: 'T', email: 't@x.test' },
  logout: vi.fn(),
  hasRole: (...roles) => roles.includes(auth.user.role),
}));
const queue = vi.hoisted(() => ({ count: 3 }));

vi.mock('../context/AuthContext', () => ({ useAuth: () => auth }));
vi.mock('../api/client', async () => {
  const actual = await vi.importActual('../api/client');
  return {
    ...actual,
    maintenanceAPI: {
      ...actual.maintenanceAPI,
      reviewQueue: () => Promise.resolve({ data: Array.from({ length: queue.count }, (_, i) => ({ id: i })) }),
    },
  };
});
vi.mock('../features/admin/TeamAccess', () => ({ default: () => <h1>Team page</h1> }));
vi.mock('../features/home/HomePage', () => ({ default: () => <h1>Home page</h1> }));

function mountApp(path) {
  return render(
    <ThemeProvider>
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>
    </ThemeProvider>,
  );
}

describe('manifest registry', () => {
  beforeEach(() => {
    auth.user.role = 'technician';
    queue.count = 3;
  });

  it('has a matching route for every nav target', () => {
    const paths = new Set(featureRoutes.map(route => route.path));
    featureNav.forEach(item => expect(paths.has(item.to), item.to).toBe(true));
  });

  it('sorts navigation by order', () => {
    const orders = featureNav.map(item => item.order);
    expect(orders).toEqual([...orders].sort((a, b) => a - b));
  });

  it('hides the admin-only item and route from a technician', async () => {
    mountApp('/app/team');
    expect(await screen.findByRole('alert')).toHaveTextContent('Access restricted');
    expect(screen.queryByRole('link', { name: 'Team & Access', exact: true })).not.toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Team page' })).not.toBeInTheDocument();
  });

  it('shows the admin-only item and route to an admin', async () => {
    auth.user.role = 'admin';
    mountApp('/app/team');
    expect(await screen.findByRole('heading', { name: 'Team page' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Team & Access', exact: true })).toBeInTheDocument();
  });

  it('renders the review badge count and refetches on halite:review-changed', async () => {
    render(
      <ThemeProvider>
        <MemoryRouter>
          <Sidebar />
        </MemoryRouter>
      </ThemeProvider>,
    );
    expect(await screen.findByLabelText('3 records awaiting review')).toBeInTheDocument();

    queue.count = 5;
    act(() => {
      window.dispatchEvent(new Event('halite:review-changed'));
    });
    await waitFor(() => expect(screen.getByLabelText('5 records awaiting review')).toBeInTheDocument());
  });
});
