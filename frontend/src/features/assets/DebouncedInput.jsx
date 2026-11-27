import { useEffect, useRef, useState } from 'react';

export const FILTER_DEBOUNCE_MS = 300;

/**
 * A text input that shows keystrokes immediately but only reports the value
 * (through onCommit) once typing has paused for `delay` milliseconds.
 * `value` is the committed value (for example from the URL); when it changes
 * from outside, the input follows it.
 */
export default function DebouncedInput({
  value,
  onCommit,
  delay = FILTER_DEBOUNCE_MS,
  ...inputProps
}) {
  const [draft, setDraft] = useState(value);
  const commitRef = useRef(onCommit);
  commitRef.current = onCommit;

  useEffect(() => {
    setDraft(value);
  }, [value]);

  useEffect(() => {
    if (draft === value) return undefined;
    const timer = setTimeout(() => commitRef.current(draft), delay);
    return () => clearTimeout(timer);
    // `value` is deliberately not a dependency: a committed change must not restart the timer.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draft, delay]);

  return <input {...inputProps} value={draft} onChange={(e) => setDraft(e.target.value)} />;
}
