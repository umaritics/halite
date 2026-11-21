import { useState } from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import SourceNarrative, { narrativeSegments } from '../features/investigation/SourceNarrative';
import { GroundedReply } from '../features/investigation/DecisionView';

const annotation = spans => ({ version: 'content-token-spans-v1', encoding: 'utf-16', spans });
const pump = annotation([{ start: 3, end: 7, token: 'pump' }, { start: 8, end: 12, token: 'leak' }]);

describe('Saved source word positions', () => {
  it('preserves exact Unicode text and marks repeated source words with browser offsets', () => {
    const text = '😀 Pump leak.';
    const { container } = render(<SourceNarrative text={text} annotation={pump} selected />);
    expect(container.querySelector('[data-source-narrative]').textContent).toBe(text);
    expect([...container.querySelectorAll('mark')].map(mark => mark.textContent)).toEqual(['Pump', 'leak']);
    expect(screen.getByText(/Highlights show word overlap/)).toBeInTheDocument();
  });
  it('rejects stale, overlapping, negative, foreign-encoding and out-of-range positions', () => {
    for (const value of [annotation([{ start: -1, end: 2, token: 'pump' }]), annotation([{ start: 3, end: 99, token: 'pump' }]), annotation([{ start: 3, end: 7, token: 'wrong' }]), annotation([{ start: 3, end: 7, token: 'pump' }, { start: 3, end: 7, token: 'pump' }]), { ...pump, encoding: 'codepoints' }]) {
      expect(narrativeSegments('😀 Pump leak.', value)).toBeNull();
    }
  });
  it('does not invent annotations for old audits and renders markup as literal source text', () => {
    const text = '<script>unsafe()</script> Pump.';
    const { container, rerender } = render(<SourceNarrative text={text} selected />);
    expect(container.querySelector('script')).toBeNull();
    expect(container.querySelector('[data-source-narrative]').textContent).toBe(text);
    expect(container.querySelector('mark')).toBeNull();
    expect(screen.getByText(/Word positions were not saved/)).toBeInTheDocument();
    rerender(<SourceNarrative text={text} annotation={annotation([])} selected />);
    expect(screen.getByText(/No matching content words/)).toBeInTheDocument();
  });
  it('switches source and marks on sentence hover and keyboard badge focus without rating changes', () => {
    const sentences = [
      { text: 'Pump leak.', level: 'unrated', citations: ['REC123456'], best_record_id: 'REC123456', candidates: [{ record_id: 'REC123456', source_matches: pump }] },
      { text: 'No report cited.', level: 'uncited', citations: [] },
      { text: 'Valve cracked.', level: 'unrated', citations: ['REC654321'], best_record_id: 'REC654321', candidates: [{ record_id: 'REC654321', source_matches: annotation([{ start: 0, end: 5, token: 'valve' }]) }] },
    ];
    function Harness() {
      const [selection, setSelection] = useState(null);
      const texts = { REC123456: '😀 Pump leak.', REC654321: 'Valve cracked.' };
      return <><GroundedReply grounding={{ status: 'thresholds_pending', checked_with: 'lexical', sentences }} onSentenceFocus={(id, sentence) => setSelection({ id, sentence })} />
        {selection?.id && <SourceNarrative text={texts[selection.id]} annotation={selection.sentence.candidates.find(candidate => candidate.record_id === selection.id).source_matches} selected />}</>;
    }
    const { container } = render(<Harness />);
    fireEvent.mouseEnter(screen.getByText('Pump leak.'));
    expect([...container.querySelectorAll('mark')].map(mark => mark.textContent)).toEqual(['Pump', 'leak']);
    fireEvent.focus(screen.getAllByLabelText(/Sentence check: unrated/)[1]);
    expect([...container.querySelectorAll('mark')].map(mark => mark.textContent)).toEqual(['Valve']);
    expect(container.querySelector('[data-source-narrative]').textContent).toBe('Valve cracked.');
    expect(screen.getByText(/Sentence ratings await validation/)).toBeInTheDocument();
    fireEvent.mouseEnter(screen.getByText('No report cited.'));
    expect(container.querySelector('mark')).toBeNull();
  });
});
