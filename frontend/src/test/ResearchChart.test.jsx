import { beforeEach, describe, expect, it } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import ResearchChart, { chartPoint } from '../components/ui/ResearchChart';

describe('Shared research chart contract', () => {
  beforeEach(() => {
    window.matchMedia = query => ({ matches: false, media: query, addEventListener() {}, removeEventListener() {} });
    globalThis.ResizeObserver = class { observe() {} unobserve() {} disconnect() {} };
  });
  it('converts absolute asymmetric intervals to relative whiskers without changing the estimate', () => {
    expect(chartPoint({ x: .4, y: .6, xCI: { low: .3, high: .6 }, yCI: { low: .4, high: .7 } })).toEqual({
      x: .4, y: .6, xCI: { low: .3, high: .6 }, yCI: { low: .4, high: .7 }, errorX: [.4 - .3, .6 - .4], errorY: [.6 - .4, .7 - .6],
    });
    expect(chartPoint({ x: 0, y: null })).toBeNull();
    expect(chartPoint({ x: 0, y: NaN })).toBeNull();
  });
  it('retains undefined accuracy in its accessible table instead of inventing zero', () => {
    render(<ResearchChart title="Saved evidence" year={2024} n={389} originals={340} resamples={1000} caption="Saved intervals" xLabel="Coverage" yLabel="Accuracy"
      series={[{ id: 'ours', label: 'Ours', role: 'ours', points: [{ x: 0, y: null, label: 'No answers' }] }]} />);
    const table = screen.getByRole('table');
    expect(within(table).getAllByText('Undefined')).toHaveLength(3);
    expect(within(table).getByText('0.0%')).toBeInTheDocument();
    expect(screen.getAllByText(/389 pairs/).length).toBeGreaterThan(0);
    expect(screen.getByText(/95% cluster-bootstrap/)).toBeInTheDocument();
  });
});
