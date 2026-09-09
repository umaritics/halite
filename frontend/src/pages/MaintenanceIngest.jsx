import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import FileUploader from '../components/FileUploader';
import { maintenanceAPI } from '../api/client';
import StatusChip from '../components/StatusChip';
import ConfidenceBar from '../components/ConfidenceBar';

export default function MaintenanceIngest() {
  const [ingestUploading, setIngestUploading] = useState(false);
  const [ingestPath, setIngestPath] = useState('data/processed/sdr_poc_corpus.csv');
  const [ingestLimit, setIngestLimit] = useState('');
  const [ingestResult, setIngestResult] = useState(null);

  const [form, setForm] = useState({
    tailNumber: '',
    date: '',
    partName: '',
    condition: '',
    location: '',
    jasc: '',
    discrepancy: ''
  });
  const [formSubmitting, setFormSubmitting] = useState(false);
  const [formResult, setFormResult] = useState(null);

  const handleCorpusIngest = async () => {
    setIngestUploading(true);
    setIngestResult(null);
    try {
      const payload = { csv_path: ingestPath };
      if (ingestLimit) payload.limit = parseInt(ingestLimit, 10);
      const { data } = await maintenanceAPI.ingest(payload);
      setIngestResult(data);
    } catch (err) {
      alert(err.response?.data?.detail || err.message || 'Ingest failed');
    } finally {
      setIngestUploading(false);
    }
  };

  const handleSingleRecordSubmit = async (e) => {
    e.preventDefault();
    setFormSubmitting(true);
    setFormResult(null);
    try {
      const payload = {
        tail_number: form.tailNumber,
        date: form.date,
        part_name: form.partName,
        condition: form.condition,
        location: form.location,
        jasc_code: form.jasc,
        discrepancy: form.discrepancy
      };
      
      const { data } = await maintenanceAPI.submitRecord(payload);
      setFormResult(data);

    } catch (err) {
      alert(err.response?.data?.detail || err.message || 'Submit failed');
    } finally {
      setFormSubmitting(false);
    }
  };

  return (
    <div className="h-full overflow-y-auto">
      <header className="border-b border-theme px-6 py-4">
        <h2 className="font-brand text-xl text-primary">Maintenance Ingest</h2>
        <p className="font-sans text-sm text-secondary">
          Import FAA SDR records or submit new service records to the knowledge graph
        </p>
      </header>

      <div className="mx-auto max-w-4xl space-y-8 p-6">
        
        {/* Panel 1: Corpus Ingest */}
        <section className="halite-card p-6">
          <h3 className="font-brand text-primary">Corpus Ingest</h3>
          <p className="mt-1 font-sans text-sm text-secondary mb-4">
            Import a batch of records from a CSV file.
          </p>
          
          <div className="grid gap-4 sm:grid-cols-2 mb-4">
            <div>
              <label className="font-sans text-sm text-secondary">CSV Path</label>
              <input
                value={ingestPath}
                onChange={(e) => setIngestPath(e.target.value)}
                className="halite-input mt-1 w-full"
                placeholder="data/processed/sdr_poc_corpus.csv"
              />
            </div>
            <div>
              <label className="font-sans text-sm text-secondary">Row Limit (Optional)</label>
              <input
                type="number"
                value={ingestLimit}
                onChange={(e) => setIngestLimit(e.target.value)}
                className="halite-input mt-1 w-full"
                placeholder="e.g. 150"
              />
            </div>
          </div>
          
          <button 
            onClick={handleCorpusIngest} 
            disabled={ingestUploading} 
            className="halite-btn-primary"
          >
            {ingestUploading ? 'Ingesting...' : 'Ingest Corpus'}
          </button>

          {ingestResult && (
            <div className="mt-6 p-4 bg-surface-dark/5 rounded border border-theme grid grid-cols-2 sm:grid-cols-5 gap-4">
              <div className="flex flex-col">
                <span className="text-secondary text-xs font-sans">Assets Created</span>
                <span className="text-primary font-mono text-lg">{ingestResult.assets_created}</span>
              </div>
              <div className="flex flex-col">
                <span className="text-secondary text-xs font-sans">Records Created</span>
                <span className="text-primary font-mono text-lg">{ingestResult.records_created}</span>
              </div>
              <div className="flex flex-col">
                <span className="text-secondary text-xs font-sans">Skipped (No Tail)</span>
                <span className="text-amber-500 font-mono text-lg">{ingestResult.rows_skipped_no_tail}</span>
              </div>
              <div className="flex flex-col">
                <span className="text-secondary text-xs font-sans">Skipped (Bad Date)</span>
                <span className="text-amber-500 font-mono text-lg">{ingestResult.rows_skipped_bad_date}</span>
              </div>
              <div className="flex flex-col">
                <span className="text-secondary text-xs font-sans">Duplicates Skipped</span>
                <span className="text-primary font-mono text-lg">{ingestResult.duplicates_skipped || 0}</span>
              </div>
            </div>
          )}
        </section>

        {/* Panel 2: Single Record Submission */}
        <section className="halite-card p-6">
          <h3 className="font-brand text-primary">Single Record Submission</h3>
          <p className="mt-1 font-sans text-sm text-secondary mb-4">
            Submit a new service record for immediate conflict resolution.
          </p>

          <form onSubmit={handleSingleRecordSubmit} className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="font-sans text-sm text-secondary">Tail Number</label>
                <input required className="halite-input mt-1 w-full" value={form.tailNumber} onChange={e => setForm({...form, tailNumber: e.target.value})} placeholder="e.g. 508AE" />
              </div>
              <div>
                <label className="font-sans text-sm text-secondary">Date</label>
                <input required type="date" className="halite-input mt-1 w-full" value={form.date} onChange={e => setForm({...form, date: e.target.value})} />
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-3">
              <div>
                <label className="font-sans text-sm text-secondary">Part Name</label>
                <input required className="halite-input mt-1 w-full" value={form.partName} onChange={e => setForm({...form, partName: e.target.value})} />
              </div>
              <div>
                <label className="font-sans text-sm text-secondary">Condition</label>
                <input className="halite-input mt-1 w-full" value={form.condition} onChange={e => setForm({...form, condition: e.target.value})} />
              </div>
              <div>
                <label className="font-sans text-sm text-secondary">Location</label>
                <input className="halite-input mt-1 w-full" value={form.location} onChange={e => setForm({...form, location: e.target.value})} />
              </div>
            </div>

            <div>
              <label className="font-sans text-sm text-secondary">JASC Code</label>
              <input className="halite-input mt-1 w-full" value={form.jasc} onChange={e => setForm({...form, jasc: e.target.value})} />
            </div>

            <div>
              <label className="font-sans text-sm text-secondary">Discrepancy Text</label>
              <textarea required rows={3} className="halite-input mt-1 w-full" value={form.discrepancy} onChange={e => setForm({...form, discrepancy: e.target.value})}></textarea>
            </div>

            <button type="submit" disabled={formSubmitting} className="halite-btn-primary">
              {formSubmitting ? 'Processing...' : 'Submit Record'}
            </button>
          </form>

          {formResult && (
            <div className="mt-6 p-4 bg-surface-dark/5 rounded border border-theme">
              <div className="flex flex-wrap items-start justify-between gap-4 mb-4">
                <div>
                  <h4 className="font-brand text-primary mb-1">Classification Result</h4>
                  <div className="flex items-center gap-3">
                    <StatusChip status={formResult.status_applied || formResult.route} />
                    <span className="text-secondary font-sans text-sm border-l border-theme pl-3">
                      Routed to: <strong className="text-primary">{formResult.route}</strong>
                    </span>
                  </div>
                </div>
                <ConfidenceBar confidence={formResult.confidence} />
              </div>
              
              <div className="font-sans text-sm text-primary mb-4 bg-surface-dark/10 p-3 rounded">
                <strong className="block text-secondary mb-1">Rationale:</strong>
                {formResult.classification?.rationale || 'N/A'}
              </div>

              {formResult.route === 'needs_review' && (
                <Link to="/app/review-queue" className="inline-flex items-center gap-2 text-accent font-sans text-sm hover:underline">
                  View in Review Queue →
                </Link>
              )}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
