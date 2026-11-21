import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, useLocation } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import App from '../App';
import { ThemeProvider } from '../context/ThemeContext';

const auth = vi.hoisted(() => ({ status: 'authenticated', isAuthenticated: true, user: { id: 'tech', role: 'technician' }, hasRole: () => false }));
vi.mock('../context/AuthContext', () => ({ useAuth: () => auth }));
vi.mock('../api/client', async () => {
  const actual = await vi.importActual('../api/client');
  return { ...actual, maintenanceAPI: { ...actual.maintenanceAPI, reviewQueue: vi.fn().mockResolvedValue({ data: [] }) } };
});
vi.mock('../features/home/HomePage', () => ({ default: () => <h1>Registered home</h1> }));
vi.mock('../features/investigation/InvestigationsPage', () => ({ default: () => <h1>Registered history</h1> }));
vi.mock('../features/investigation/InvestigationWorkspace', () => ({ default: () => <h1>Registered workspace</h1> }));
vi.mock('../features/investigation/QuickDiagnose', () => ({ default: () => <h1>Registered quick diagnosis</h1> }));
function Location() { const { pathname } = useLocation(); return <output data-testid="path">{pathname}</output>; }
function mount(path) { return render(<ThemeProvider><MemoryRouter initialEntries={[path]}><App /><Location /></MemoryRouter></ThemeProvider>); }

describe('Production feature route registration', () => {
  beforeEach(() => { auth.isAuthenticated = true; auth.status = 'authenticated'; });
  it.each(['/app', '/app/chat', '/app/not-a-route'])('redirects %s to registered home', async path => {
    mount(path);
    expect(await screen.findByRole('heading', { name: 'Registered home' })).toBeInTheDocument();
    expect(screen.getByTestId('path')).toHaveTextContent('/app/home');
  });
  it.each([
    ['/app/investigations', 'Registered history'],
    ['/app/investigations/example-id', 'Registered workspace'],
    ['/app/investigations/quick', 'Registered quick diagnosis'],
    ['/app/diagnostics', 'Registered history'],
  ])('registers %s under the protected shell', async (path, heading) => {
    mount(path);
    expect(await screen.findByRole('heading', { name: heading })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Home', exact: true })).toHaveAttribute('href', '/app/home');
    expect(screen.getByRole('link', { name: 'Investigations', exact: true })).toHaveAttribute('href', '/app/investigations');
    expect(screen.queryByRole('link', { name: 'Diagnostics', exact: true })).not.toBeInTheDocument();
  });
  it('requires authentication for a direct saved investigation URL', async () => {
    auth.isAuthenticated = false; auth.status = 'unauthenticated';
    mount('/app/investigations/private-id');
    expect(await screen.findByRole('heading', { name: /sign in to workspace/i })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Registered workspace' })).not.toBeInTheDocument();
  });
});
