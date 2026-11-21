import { Fragment } from 'react';

export function narrativeSegments(text, annotation) {
  if (annotation?.version !== 'content-token-spans-v1' || annotation.encoding !== 'utf-16' || !Array.isArray(annotation.spans)) return null;
  const segments = [];
  let offset = 0;
  for (const span of annotation.spans) {
    if (!Number.isInteger(span.start) || !Number.isInteger(span.end) || span.start < offset || span.end <= span.start || span.end > text.length
      || typeof span.token !== 'string' || text.slice(span.start, span.end).toLowerCase() !== span.token) return null;
    if (span.start > offset) segments.push({ text: text.slice(offset, span.start), match: false });
    segments.push({ text: text.slice(span.start, span.end), match: true });
    offset = span.end;
  }
  if (offset < text.length) segments.push({ text: text.slice(offset), match: false });
  return segments;
}

export default function SourceNarrative({ text, annotation, selected = false }) {
  const narrative = text || 'No narrative was saved.';
  const segments = selected && text ? narrativeSegments(narrative, annotation) : null;
  return <div>
    {selected && <p className="mt-2 text-xs text-secondary">{segments ? (segments.some(segment => segment.match) ? 'Highlights show word overlap with the selected sentence.' : 'No matching content words occur in this saved narrative.') : 'Word positions were not saved or could not be matched to this narrative.'}</p>}
    <p data-source-narrative className="mt-2 whitespace-pre-wrap break-words text-sm text-primary">{segments ? segments.map((segment, index) => segment.match
      ? <mark key={index} className="rounded-sm bg-amber-200 text-black">{segment.text}</mark>
      : <Fragment key={index}>{segment.text}</Fragment>) : narrative}</p>
  </div>;
}
