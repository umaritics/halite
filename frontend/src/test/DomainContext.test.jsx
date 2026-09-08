import React from 'react';
import { render, screen, act } from '@testing-library/react';
import { DomainProvider, useDomain } from '../context/DomainContext';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as client from '../api/client';

// Mock client
vi.mock('../api/client', () => ({
  domainsAPI: {
    list: vi.fn()
  }
}));

const TestComponent = () => {
  const { domain, setDomain } = useDomain();
  return (
    <div>
      <span data-testid="domain-val">{domain}</span>
      <button onClick={() => setDomain('maintenance')}>Set Maintenance</button>
    </div>
  );
};

describe('DomainContext', () => {
  beforeEach(() => {
    localStorage.clear();
    client.domainsAPI.list.mockResolvedValue({ data: [{ key: 'software' }] });
  });

  it('defaults to software and persists change', async () => {
    const { unmount } = render(
      <DomainProvider>
        <TestComponent />
      </DomainProvider>
    );
    
    expect(screen.getByTestId('domain-val')).toHaveTextContent('software');
    
    act(() => {
      screen.getByText('Set Maintenance').click();
    });
    
    expect(screen.getByTestId('domain-val')).toHaveTextContent('maintenance');
    expect(localStorage.getItem('halite.domain')).toBe('maintenance');
    
    unmount();
    
    // Remount to check persistence
    render(
      <DomainProvider>
        <TestComponent />
      </DomainProvider>
    );
    expect(screen.getByTestId('domain-val')).toHaveTextContent('maintenance');
  });
});
