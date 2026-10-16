import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import { describe, it, expect, vi } from 'vitest';

// Mock theme context
vi.mock('../context/ThemeContext', () => ({
  useTheme: () => ({ isDark: true })
}));

const renderSidebar = (props = {}) =>
  render(
    <MemoryRouter>
      <Sidebar {...props} />
    </MemoryRouter>
  );

describe('Sidebar', () => {
  it('renders the maintenance destinations', () => {
    renderSidebar();
    ['Assets', 'Service Records', 'Diagnostics', 'Review Queue', 'Knowledge Graph'].forEach((label) => {
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

  it('shows the review count badge only when records await review', () => {
    const { unmount } = renderSidebar({ reviewCount: 0 });
    expect(screen.queryByLabelText(/awaiting review/i)).not.toBeInTheDocument();
    unmount();

    renderSidebar({ reviewCount: 9 });
    expect(screen.getByLabelText('9 records awaiting review')).toBeInTheDocument();
  });
});
