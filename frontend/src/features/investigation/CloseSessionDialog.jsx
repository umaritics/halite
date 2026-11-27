import { useEffect, useRef, useState } from 'react';

export default function CloseSessionDialog({ pending, onCancel, onSubmit, error }) {
  const [note, setNote] = useState('');
  const [part, setPart] = useState('');
  const [jasc, setJasc] = useState('');
  const dialog = useRef(null);
  useEffect(() => {
    const node = dialog.current;
    if (node?.showModal) node.showModal();
    else node?.setAttribute('open', '');
    return () => node?.close?.();
  }, []);
  return <dialog ref={dialog} aria-labelledby="close-investigation-title" className="halite-card m-auto w-[min(90vw,36rem)] p-6 text-primary backdrop:bg-black/60"
    onCancel={event => { event.preventDefault(); if (!pending) onCancel(); }}>
    <form onSubmit={event => { event.preventDefault(); if (note.trim()) onSubmit({ outcome_note: note.trim(), outcome_part: part.trim() || null, outcome_jasc: jasc.trim() || null }); }}>
      <h2 id="close-investigation-title" className="font-brand text-xl">Close investigation</h2>
      <p className="mt-2 text-sm text-secondary">What did you find? This improves future rankings. The closed investigation will be read only.</p>
      <fieldset disabled={pending} className="mt-4 space-y-3">
        <label className="block text-sm">Finding or outcome (required)<textarea autoFocus required maxLength={4000} className="halite-input mt-1" value={note} onChange={event => setNote(event.target.value)} /></label>
        <label className="block text-sm">Part found (optional)<input maxLength={200} className="halite-input mt-1" value={part} onChange={event => setPart(event.target.value)} /></label>
        <label className="block text-sm">JASC code (optional)<input maxLength={20} className="halite-input mt-1" value={jasc} onChange={event => setJasc(event.target.value)} /></label>
        {error && <p role="alert" className="text-sm text-red-400">{error}</p>}
        <div className="flex flex-wrap justify-end gap-3">
          <button type="button" className="halite-btn-ghost px-4 py-2" onClick={onCancel}>Cancel</button>
          <button className="halite-btn-primary disabled:opacity-50" disabled={!note.trim() || pending}>{pending ? 'Saving outcome…' : 'Close with outcome'}</button>
        </div>
      </fieldset>
    </form>
  </dialog>;
}
