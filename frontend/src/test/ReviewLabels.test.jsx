import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import StatusChip from '../components/StatusChip';
import { ANALYSIS_LABELS, STATUS_LABELS, labelText } from '../lib/reviewLabels';

describe('review label mapping', () => {
  it('maps every analysis label to readable words', () => {
    expect(Object.keys(ANALYSIS_LABELS).sort()).toEqual(
      ['contradicts', 'no_conflict', 'partial_supersedes', 'scope_disjoint', 'supersedes']
    );
    expect(labelText('no_conflict')).toBe('No conflict');
    expect(labelText('scope_disjoint')).toBe('Different scope');
    expect(labelText('supersedes')).toBe('Supersedes');
    expect(labelText('partial_supersedes')).toBe('Partially supersedes');
    expect(labelText('contradicts')).toBe('Contradicts');
  });

  it('maps every status to readable words', () => {
    expect(Object.keys(STATUS_LABELS).sort()).toEqual(
      ['accepted', 'auto_accepted', 'needs_review', 'no_action', 'rejected', 'superseded', 'unscored']
    );
    expect(labelText('unscored')).toBe('Not analysed');
    expect(labelText('no_action')).toBe('No action needed');
    expect(labelText('auto_accepted')).toBe('Auto Accepted');
    expect(labelText('needs_review')).toBe('Needs Review');
  });

  it('never shows an underscore for any known or unknown value', () => {
    const values = [...Object.keys(ANALYSIS_LABELS), ...Object.keys(STATUS_LABELS), 'some_new_value'];
    values.forEach((value) => expect(labelText(value)).not.toMatch(/_/));
    expect(labelText('some_new_value')).toBe('Some new value');
  });

  it('StatusChip renders the words, not the raw value', () => {
    render(
      <>
        <StatusChip status="partial_supersedes" />
        <StatusChip status="scope_disjoint" />
        <StatusChip status="no_action" />
      </>
    );
    expect(screen.getByText('Partially supersedes')).toBeInTheDocument();
    expect(screen.getByText('Different scope')).toBeInTheDocument();
    expect(screen.getByText('No action needed')).toBeInTheDocument();
    expect(screen.queryByText(/_/)).toBeNull();
  });
});
