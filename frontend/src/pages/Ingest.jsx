import { useState } from 'react';
import FileUploader from '../components/FileUploader';
import { ingestAPI } from '../api/client';

export default function Ingest() {
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [owner, setOwner] = useState('umarific');
  const [repo, setRepo] = useState('halite-demo');
  const [syncing, setSyncing] = useState(false);
  const [codeAnalyzing, setCodeAnalyzing] = useState(false);
  const [syncResult, setSyncResult] = useState(null);
  const [codeResult, setCodeResult] = useState(null);
  const [lastSync, setLastSync] = useState(null);

  const handleUpload = async (file) => {
    setUploading(true);
    setUploadResult(null);
    const formData = new FormData();
    formData.append('file', file);
    try {
      const { data } = await ingestAPI.document(formData);
      setUploadResult(data);
    } catch (err) {
      alert(err.message || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleGiteaSync = async () => {
    setSyncing(true);
    setSyncResult(null);
    try {
      const { data } = await ingestAPI.gitea(owner, repo);
      setSyncResult(data);
      setLastSync(new Date().toLocaleString());
    } catch (err) {
      alert(err.message || 'Sync failed');
    } finally {
      setSyncing(false);
    }
  };

  const handleCodeAnalyze = async () => {
    setCodeAnalyzing(true);
    setCodeResult(null);
    try {
      const { data } = await ingestAPI.code(owner, repo);
      setCodeResult(data);
    } catch (err) {
      alert(err.message || 'Code analysis failed');
    } finally {
      setCodeAnalyzing(false);
    }
  };

  return (
    <div className="h-full overflow-y-auto">
      <header className="border-b border-theme px-6 py-4">
        <h2 className="font-brand text-xl text-primary">Ingest</h2>
        <p className="font-sans text-sm text-secondary">
          Upload documents or sync from Gitea to populate the knowledge graph
        </p>
      </header>

      <div className="mx-auto max-w-3xl space-y-8 p-6">
        <section className="halite-card p-6">
          <h3 className="font-brand text-primary">Upload Document</h3>
          <p className="mt-1 font-sans text-sm text-secondary">
            Meeting transcripts, design docs — decisions are extracted automatically
          </p>
          <div className="mt-4">
            <FileUploader onUpload={handleUpload} uploading={uploading} result={uploadResult} />
          </div>
        </section>

        <section className="halite-card p-6">
          <h3 className="font-brand text-primary">Gitea Sync</h3>
          <p className="mt-1 font-sans text-sm text-secondary">
            Pull commits, issues, and analyze code from a repository
          </p>

          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <div>
              <label className="font-sans text-sm text-secondary">Owner</label>
              <input
                value={owner}
                onChange={(e) => setOwner(e.target.value)}
                className="halite-input mt-1"
                placeholder="username"
              />
            </div>
            <div>
              <label className="font-sans text-sm text-secondary">Repository</label>
              <input
                value={repo}
                onChange={(e) => setRepo(e.target.value)}
                className="halite-input mt-1"
                placeholder="repo-name"
              />
            </div>
          </div>

          <div className="mt-4 flex flex-wrap gap-3">
            <button onClick={handleGiteaSync} disabled={syncing} className="halite-btn-primary">
              {syncing ? 'Syncing…' : 'Sync Commits & Issues'}
            </button>
            <button onClick={handleCodeAnalyze} disabled={codeAnalyzing} className="halite-btn-ghost">
              {codeAnalyzing ? 'Analyzing…' : 'Analyze Code'}
            </button>
          </div>

          {lastSync && (
            <p className="mt-3 font-sans text-xs text-[#555555]">Last sync: {lastSync}</p>
          )}

          {syncResult && (
            <p className="mt-3 font-sans text-sm text-accent">
              Synced {syncResult.commits_synced} commit(s), {syncResult.tickets_synced} ticket(s)
            </p>
          )}
          {codeResult && (
            <p className="mt-3 font-sans text-sm text-accent">
              Processed {codeResult.files_processed} file(s), created {codeResult.components_created} component(s)
              {codeResult.demo && ' (demo mode)'}
            </p>
          )}
        </section>
      </div>
    </div>
  );
}
