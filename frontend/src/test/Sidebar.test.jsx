import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import { DomainContext } from '../context/DomainContext';
import { describe, it, expect, vi } from 'vitest';

// Mock theme context
vi.mock('../context/ThemeContext', () => ({
  useTheme: () => ({ isDark: true })
}));

describe('Sidebar', () => {
  it('renders software nav items by default', () => {
    render(
      <MemoryRouter>
        <DomainContext.Provider value={{ domain: 'software', domains: [] }}>
          <Sidebar />
        </DomainContext.Provider>
      </MemoryRouter>
    );
    expect(screen.getByText('Decisions')).toBeInTheDocument();
    expect(screen.queryByText('Assets')).not.toBeInTheDocument();
  });

  it('renders maintenance nav items when in maintenance domain', () => {
    render(
      <MemoryRouter>
        <DomainContext.Provider value={{ domain: 'maintenance', domains: [] }}>
          <Sidebar />
        </DomainContext.Provider>
      </MemoryRouter>
    );
    expect(screen.getByText('Assets')).toBeInTheDocument();
    expect(screen.queryByText('Decisions')).not.toBeInTheDocument();
  });
});
