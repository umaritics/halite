import { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { CloudArrowUpIcon, DocumentIcon } from '@heroicons/react/24/outline';

const ACCEPTED = {
  'application/pdf': ['.pdf'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
  'text/plain': ['.txt'],
  'text/markdown': ['.md'],
};

export default function FileUploader({ onUpload, uploading, result }) {
  const onDrop = useCallback(
    (files) => {
      if (files[0]) onUpload(files[0]);
    },
    [onUpload]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED,
    maxFiles: 1,
    disabled: uploading,
  });

  return (
    <div>
      <div
        {...getRootProps()}
        className={`cursor-pointer rounded-xl border-2 border-dashed p-10 text-center transition ${
          isDragActive
            ? 'border-accent bg-accent/5'
            : 'border-theme hover:border-accent hover:bg-surface'
        } ${uploading ? 'pointer-events-none opacity-60' : ''}`}
      >
        <input {...getInputProps()} />
        <CloudArrowUpIcon className="mx-auto h-12 w-12 text-accent/60" />
        <p className="mt-3 font-sans text-sm text-primary">
          {isDragActive ? 'Drop the file here…' : 'Drag & drop a document, or click to browse'}
        </p>
        <p className="mt-1 font-sans text-xs text-[#555555]">PDF, DOCX, TXT, MD — max 10MB</p>
      </div>

      {uploading && (
        <div className="mt-4 flex items-center gap-2 font-sans text-sm text-accent">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-accent border-t-transparent" />
          Processing document and extracting decisions…
        </div>
      )}

      {result && (
        <div className="mt-4 flex items-center gap-3 rounded-lg bg-accent/10 p-4 ring-1 ring-accent/20">
          <DocumentIcon className="h-5 w-5 text-accent" />
          <p className="font-sans text-sm text-accent">
            Extracted <strong>{result.decisions_created}</strong> decision(s) from document.
          </p>
        </div>
      )}
    </div>
  );
}
