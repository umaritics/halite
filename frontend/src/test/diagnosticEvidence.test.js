import { describe, expect, it } from 'vitest';

import {
  caseIssueLabels,
  classifyEvidenceProvenance,
  groupEvidenceRecords,
  historicalIssueDiff,
} from '../utils/diagnosticEvidence';

const assets = [
  { id: 'asset-813', tail_number: '813SK' },
  { id: 'asset-173', tail_number: '173US' },
];

describe('diagnostic evidence provenance and grouping', () => {
  it('matches only exact known aircraft identifiers, never loose substrings', () => {
    expect(classifyEvidenceProvenance({ asset_id: '813SK' }, 'asset-813', assets).kind).toBe('same');
    expect(classifyEvidenceProvenance({ asset_id: 'asset-813' }, 'asset-813', assets).kind).toBe('same');
    expect(classifyEvidenceProvenance({ asset_id: 'X813SK' }, 'asset-813', assets).kind).toBe('other');
    expect(classifyEvidenceProvenance({ asset_id: 'N813SK' }, 'asset-813', assets).kind).toBe('other');
    expect(classifyEvidenceProvenance({}, 'asset-813', assets).kind).toBe('unknown');
    expect(classifyEvidenceProvenance({ asset_id: '173US' }, '', assets).kind).toBe('unknown');
  });

  it('groups only records grounded to the same aircraft, component, and condition', () => {
    const records = new Map([
      ['R1', { record_id: 'R1', asset_id: '173US', part_name: 'SUPPORT FRAME', part_condition: 'EXCESSIVE PLAY' }],
      ['R2', { record_id: 'R2', asset_id: '173US', part_name: 'SUPPORT FRAME', text: 'Excessive play found.' }],
      ['R3', { record_id: 'R3', asset_id: '173US', part_name: 'SUPPORT FRAME', part_condition: 'CRACKED' }],
      ['R4', { record_id: 'R4', asset_id: '813SK', part_name: 'SUPPORT FRAME', part_condition: 'EXCESSIVE PLAY' }],
    ]);

    const groups = groupEvidenceRecords(['R1', 'R2', 'R3', 'R4', 'MISSING'], records, 'asset-813', assets);
    expect(groups).toHaveLength(4);
    expect(groups.find(group => group.records.some(item => item.recordId === 'R1')).records.map(item => item.recordId)).toEqual(['R1', 'R2']);
    expect(groups.find(group => group.records.some(item => item.recordId === 'R3')).condition).toBe('CRACKED');
    expect(groups.find(group => group.records.some(item => item.recordId === 'R4')).provenance.kind).toBe('same');
    expect(groups.find(group => group.records.some(item => item.recordId === 'MISSING')).provenance.kind).toBe('unknown');
  });

  it('reports a discrepancy difference only when grounded issue labels differ', () => {
    const current = caseIssueLabels({ symptoms: [], observations: ['Crack observed near support'] });
    expect(current).toEqual(['crack']);
    expect(historicalIssueDiff('EXCESSIVE PLAY', current)).toEqual({ historical: ['excessive play'], current: ['crack'] });
    expect(historicalIssueDiff('CRACKED', current)).toBeNull();
    expect(historicalIssueDiff('UNKNOWN CONDITION', current)).toBeNull();
    expect(caseIssueLabels({ symptoms: [], observations: ['No crack observed in the stringer splice'] })).toEqual([]);
  });
});
