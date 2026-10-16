import { describe, it, expect } from 'vitest';
import { formatDetail, describeDiagnosticError, extractExplanation } from '../utils/diagnostics';

describe('formatDetail', () => {
  it('passes strings through', () => {
    expect(formatDetail('plain message')).toBe('plain message');
  });

  it('flattens FastAPI validation arrays to text', () => {
    expect(
      formatDetail([
        { loc: ['body', 'symptom_text'], msg: 'Field required', type: 'missing' },
        { loc: ['body', 'asset_id'], msg: 'Input should be a valid string', type: 'string_type' },
      ])
    ).toBe('symptom_text: Field required; asset_id: Input should be a valid string');
  });

  it('returns null for empty or unusable detail', () => {
    expect(formatDetail(undefined)).toBeNull();
    expect(formatDetail([])).toBeNull();
    expect(formatDetail({ some: 'object' })).toBeNull();
  });
});

describe('describeDiagnosticError', () => {
  const http = (status, detail) => ({ response: { status, data: { detail } }, message: 'x' });

  it.each([
    [404, 'no-history', false],
    [422, 'validation', false],
    [503, 'model-unavailable', true],
    [429, 'rate-limited', true],
    [500, 'server-error', true],
    [502, 'server-error', true],
  ])('maps HTTP %i to %s (retryable: %s)', (status, kind, retryable) => {
    const d = describeDiagnosticError(http(status, 'detail text'));
    expect(d.kind).toBe(kind);
    expect(d.retryable).toBe(retryable);
    expect(d.title).toBeTruthy();
    expect(d.message).toBeTruthy();
  });

  it('keeps the backend detail for 503 so the limitation is explained', () => {
    expect(describeDiagnosticError(http(503, 'Groq LLM is not configured')).detail).toBe('Groq LLM is not configured');
  });

  it('always returns strings, never objects, even for array detail', () => {
    const d = describeDiagnosticError(http(422, [{ loc: ['body', 'x'], msg: 'bad' }]));
    expect(typeof d.detail).toBe('string');
    expect(typeof d.message).toBe('string');
  });

  it('detects a network failure', () => {
    expect(describeDiagnosticError({ code: 'ERR_NETWORK', message: 'Network Error' }).kind).toBe('network');
  });

  it('does not call an unrelated thrown error a network failure', () => {
    const d = describeDiagnosticError(new TypeError('x is not a function'));
    expect(d.kind).toBe('unknown');
    expect(d.message).toBe('x is not a function');
  });

  it('falls back to the backend detail when there is no status', () => {
    const d = describeDiagnosticError({ response: { data: { detail: 'Something went wrong' } } });
    expect(d.message).toBe('Something went wrong');
  });
});

describe('extractExplanation', () => {
  it('returns ordinary prose untouched', () => {
    expect(extractExplanation('DRAG ANGLE is top-ranked.')).toEqual({
      text: 'DRAG ANGLE is top-ranked.',
      warnings: [],
      recovered: false,
    });
  });

  it('unwraps a raw JSON blob from the model', () => {
    const r = extractExplanation('{"explanation": "Readable text.", "rare_cases": ["A1"], "warnings": ["Careful."]}');
    expect(r.text).toBe('Readable text.');
    expect(r.warnings).toEqual(['Careful.']);
    expect(r.recovered).toBe(true);
  });

  it('unwraps JSON inside a markdown fence', () => {
    const r = extractExplanation('```json\n{"explanation": "Fenced text."}\n```');
    expect(r.text).toBe('Fenced text.');
  });

  it('recovers the explanation from truncated JSON', () => {
    const r = extractExplanation('{\n  "explanation": "First line.\\nSecond line, cut off mid');
    expect(r.recovered).toBe(true);
    expect(r.text).toContain('First line.');
    expect(r.text).toContain('Second line');
    expect(r.text).not.toContain('"explanation"');
  });

  it('leaves JSON without an explanation key alone', () => {
    const raw = '{"foo": "bar"}';
    expect(extractExplanation(raw).text).toBe(raw);
    expect(extractExplanation(raw).recovered).toBe(false);
  });

  it('handles non-string input', () => {
    expect(extractExplanation(undefined).text).toBe('');
    expect(extractExplanation(null).text).toBe('');
  });
});
