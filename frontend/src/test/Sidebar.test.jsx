import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import { describe, it, expect, vi } from 'vitest';

// Mock theme context
const queue = vi.hoisted(() => ({ count: 0 }));
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

vi.mock('../context/ThemeContext', () => ({
  useTheme: () => ({ isDark: true })
}));

const renderSidebar = () =>
  render(
    <MemoryRouter>
      <Sidebar />
    </MemoryRouter>
  );

describe('Sidebar', () => {
  it('renders the maintenance destinations', () => {
    renderSidebar();
    ['Home', 'Assets', 'Service Records', 'Investigations', 'Review Queue', 'Knowledge Graph'].forEach((label) => {
      expect(screen.getByText(label)).toBeInTheDocument();
    });
  });

  it('does not expose dropped software-domain screens or a domain switcher', () => {
    renderSidebar();
    ['Chat', 'Decisions', 'Alerts', 'Software'].forEach((label) => {
      expect(screen.queryByText(label)).not.toBeInTheDocument();
    });
    expect(screen.queryByRole('link', { name: /decisions|chat|alerts/i })).not.toBeInTheDocument();
  });

  it('shows the review count badge only when records await review', async () => {
    queue.count = 0;
    const { unmount } = renderSidebar();
    await screen.findByText('Review Queue');
    expect(screen.queryByLabelText(/awaiting review/i)).not.toBeInTheDocument();
    unmount();

    queue.count = 9;
    renderSidebar();
    expect(await screen.findByLabelText('9 records awaiting review')).toBeInTheDocument();
  });
});
