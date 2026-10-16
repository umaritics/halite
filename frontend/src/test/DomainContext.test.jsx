import React from 'react';
import { render, screen, act } from '@testing-library/react';
import { DomainProvider, useDomain } from '../context/DomainContext';
import { describe, it, expect, beforeEach } from 'vitest';

const TestComponent = () => {
  const { domain, setDomain } = useDomain();
  return (
    <div>
      <span data-testid="domain-val">{domain}</span>
      <button onClick={() => setDomain('software')}>Try Software</button>
    </div>
  );
};

describe('DomainContext', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('is locked to the maintenance domain', () => {
    render(
      <DomainProvider>
        <TestComponent />
      </DomainProvider>
    );
    expect(screen.getByTestId('domain-val')).toHaveTextContent('maintenance');
  });

  it('ignores a stale software value left in localStorage by the old switcher', () => {
    localStorage.setItem('halite.domain', 'software');
    render(
      <DomainProvider>
        <TestComponent />
      </DomainProvider>
    );
    expect(screen.getByTestId('domain-val')).toHaveTextContent('maintenance');
  });

  it('cannot be switched to the software domain', () => {
    render(
      <DomainProvider>
        <TestComponent />
      </DomainProvider>
    );
    act(() => {
      screen.getByText('Try Software').click();
    });
    expect(screen.getByTestId('domain-val')).toHaveTextContent('maintenance');
    expect(localStorage.getItem('halite.domain')).toBeNull();
  });
});
