import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { CloudArrowUpIcon, DocumentTextIcon } from '@heroicons/react/24/outline';
import { maintenanceAPI } from '../api/client';
import { describeLoadError } from '../utils/loadError';
import IngestResult from './IngestResult';

// Mirrors the backend default MAX_UPLOAD_MB (backend/config.py); the server still enforces its own limit (HTTP 413).
export const MAX_UPLOAD_MB = 10;
const ACCEPT = { 'text/csv': ['.csv'], 'application/vnd.ms-excel': ['.csv'] };

const REJECTIONS = {
  'file-too-large': `That file is larger than ${MAX_UPLOAD_MB} MB.`,
  'file-invalid-type': 'Only .csv files can be ingested.',
  'too-many-files': 'Choose one file at a time.',
};

const fmtSize = (bytes) => (bytes < 1024 * 1024 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`);

// The API answers an unparseable CSV (e.g. an empty file) with an unhandled HTTP 500 that has no CORS headers,
// so a browser reports it as a network failure. For an upload, "API not running" would be a misleading diagnosis.
const FILE_HINT = 'Check that the file is a CSV with a header row and the required columns, then try again.';
function uploadMessage(d) {
  if (d.kind === 'network') {
    return `The upload failed and the server sent no readable reply. The API may be unreachable, or it could not read the file. ${FILE_HINT}`;
  }
  if (d.kind === 'server') return `${d.message} ${FILE_HINT}`;
  return d.message;
}

// Two steps on purpose: choosing a file changes nothing; "Ingest this file" writes to the connected graph.
export default function CsvUploader() {
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [done, setDone] = useState(null); // { name, result }

  const onDrop = useCallback((accepted, rejected) => {
    setDone(null);
    if (rejected.length) {
      const code = rejected[0].errors?.[0]?.code;
      setError(REJECTIONS[code] || 'That file cannot be ingested.');
      return;
    }
    setError(null);
    if (accepted[0]) setFile(accepted[0]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPT,
    maxFiles: 1,
    maxSize: MAX_UPLOAD_MB * 1024 * 1024,
    disabled: busy,
  });

  const submit = async () => {
    setBusy(true);
    setError(null);
    setDone(null);
    try {
      const body = new FormData();
      body.append('file', file);
      const { data } = await maintenanceAPI.ingestFile(body);
      setDone({ name: file.name, result: data });
      setFile(null);
    } catch (err) {
      const d = describeLoadError(err);
      setError(uploadMessage(d));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <div
        {...getRootProps()}
        className={`cursor-pointer rounded-xl border-2 border-dashed p-8 text-center transition ${
          isDragActive ? 'border-accent bg-accent/5' : 'border-theme hover:border-accent hover:bg-surface'
        } ${busy ? 'pointer-events-none opacity-60' : ''}`}
      >
        <input {...getInputProps({ 'aria-label': 'CSV file' })} />
        <CloudArrowUpIcon className="mx-auto h-10 w-10 text-accent/60" />
        <p className="mt-2 font-sans text-sm text-primary">
          {isDragActive ? 'Drop the file here…' : 'Drag & drop a CSV, or click to browse'}
        </p>
        <p className="mt-1 font-sans text-xs text-[#555555]">.csv only — max {MAX_UPLOAD_MB} MB</p>
      </div>

      {file && (
        <div id="csv-selected" className="mt-4 flex flex-wrap items-center gap-3 font-sans text-sm text-primary">
          <DocumentTextIcon className="h-5 w-5 text-accent" />
          <span>{file.name}</span>
          <span className="text-secondary">{fmtSize(file.size)}</span>
          <button type="button" onClick={submit} disabled={busy} className="halite-btn-primary">
            {busy ? 'Ingesting…' : 'Ingest this file'}
          </button>
          <button type="button" onClick={() => setFile(null)} disabled={busy} className="halite-btn-ghost">
            Choose a different file
          </button>
        </div>
      )}
      <p className="mt-3 font-sans text-xs text-[#555555]">
        Ingesting writes to the connected graph. Uploading the same file again is safe: records already stored are
        counted as already in graph and left unchanged.
      </p>

      {error && (
        <p role="alert" className="mt-4 rounded-md bg-red-500/10 px-3 py-2 font-sans text-sm text-red-400">
          {error}
        </p>
      )}
      {done && (
        <>
          <p className="mt-4 font-sans text-sm text-secondary">
            Ingested <span className="text-primary">{done.name}</span>
          </p>
          <IngestResult result={done.result} />
        </>
      )}
    </div>
  );
}
