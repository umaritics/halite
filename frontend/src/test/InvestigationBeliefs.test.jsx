import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { BeliefBars } from '../features/investigation/DecisionView';

describe('Historical relative-support presentation', () => {
  it('shows named and other buckets, explicit calibration status and entropy', () => {
    render(<BeliefBars beliefs={{ hypotheses: [{ part_name: 'PUMP', belief: .5 }], other: .5, entropy: 1, calibrated: false }} />);
    expect(screen.getByRole('meter', { name: 'PUMP' })).toHaveAttribute('aria-valuenow', '0.5');
    expect(screen.getByRole('meter', { name: 'Other / outside ranking' })).toHaveAttribute('aria-valuetext', '50.0% relative support');
    expect(screen.getByText(/Uncalibrated historical support/)).toBeInTheDocument();
    expect(screen.getByText('Uncertainty: 1.00 bits, including other.')).toBeInTheDocument();
    expect(screen.queryByText(/probability/i)).not.toBeInTheDocument();
  });
  it('retains the other bucket with an empty ranking and keeps fitted bars labelled relative support', () => {
    const { rerender } = render(<BeliefBars beliefs={{ hypotheses: [], other: 1, entropy: 0, calibrated: false }} />);
    expect(screen.getAllByRole('meter')).toHaveLength(1);
    expect(screen.getByRole('meter')).toHaveAttribute('aria-valuenow', '1');
    rerender(<BeliefBars beliefs={{ hypotheses: [{ part_name: 'SENSOR', belief: .4 }], other: .6, calibrated: true }} />);
    expect(screen.getByRole('region', { name: 'Relative support' })).toBeInTheDocument();
    expect(screen.getByText(/Fitted historical support/)).toBeInTheDocument();
  });
});
