import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import CsvUploader from './CsvUploader';
import CorpusIngestPanel from './CorpusIngestPanel';
import { maintenanceAPI } from '../../api/client';
import StatusChip from '../../components/StatusChip';
import ConfidenceBar from '../../components/ConfidenceBar';
import { describeLoadError } from '../../utils/loadError';
import { useAuth } from '../../context/AuthContext';
import { Button, PageHeader } from '../../components/ui';

export default function MaintenanceIngest() {
  const { hasRole } = useAuth();
  const isAdmin = hasRole('admin');

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
  const [formError, setFormError] = useState(null);

  const handleSingleRecordSubmit = async (e) => {
    e.preventDefault();
    setFormSubmitting(true);
    setFormResult(null);
    setFormError(null);
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
      setFormError(describeLoadError(err).message);
    } finally {
      setFormSubmitting(false);
    }
  };

  return (
    <div className="h-full overflow-y-auto">
      <div className="px-6 pt-4">
        <PageHeader
          title="Maintenance Ingest"
          description="Import FAA SDR records or submit a single service record to the graph"
        />
      </div>

      <div className="mx-auto max-w-4xl space-y-8 p-6">
        {/* Panel 1: CSV upload */}
        <section className="halite-card p-6">
          <h3 className="font-brand text-primary">Upload CSV</h3>
          <p className="mb-4 mt-1 font-sans text-sm text-secondary">
            Import FAA SDR records from a CSV on your computer. Required columns: RegistryNNumber, DifficultyDate
            (MM/DD/YYYY), OperatorControlNumber.
          </p>
          <CsvUploader />
        </section>

        {/* Panel 2: Corpus Ingest (file already on the API server), admins only */}
        {isAdmin && <CorpusIngestPanel />}

        {/* Panel 3: Single Record Submission */}
        <section className="halite-card p-6">
          <h3 className="font-brand text-primary">Single Record Submission</h3>
          <p className="mt-1 font-sans text-sm text-secondary mb-4">
            Submit a new service record for immediate conflict resolution.
          </p>

          <form onSubmit={handleSingleRecordSubmit} className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label htmlFor="form-tail" className="font-sans text-sm text-secondary">Tail Number</label>
                <input id="form-tail" required className="halite-input mt-1 w-full" value={form.tailNumber} onChange={e => setForm({...form, tailNumber: e.target.value})} placeholder="e.g. 508AE" />
              </div>
              <div>
                <label htmlFor="form-date" className="font-sans text-sm text-secondary">Date</label>
                <input id="form-date" required type="date" className="halite-input mt-1 w-full" value={form.date} onChange={e => setForm({...form, date: e.target.value})} />
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-3">
              <div>
                <label htmlFor="form-part" className="font-sans text-sm text-secondary">Part Name</label>
                <input id="form-part" required className="halite-input mt-1 w-full" value={form.partName} onChange={e => setForm({...form, partName: e.target.value})} />
              </div>
              <div>
                <label htmlFor="form-condition" className="font-sans text-sm text-secondary">Condition</label>
                <input id="form-condition" className="halite-input mt-1 w-full" value={form.condition} onChange={e => setForm({...form, condition: e.target.value})} />
              </div>
              <div>
                <label htmlFor="form-location" className="font-sans text-sm text-secondary">Location</label>
                <input id="form-location" className="halite-input mt-1 w-full" value={form.location} onChange={e => setForm({...form, location: e.target.value})} />
              </div>
            </div>

            <div>
              <label htmlFor="form-jasc" className="font-sans text-sm text-secondary">JASC Code</label>
              <input id="form-jasc" className="halite-input mt-1 w-full" value={form.jasc} onChange={e => setForm({...form, jasc: e.target.value})} />
            </div>

            <div>
              <label htmlFor="form-text" className="font-sans text-sm text-secondary">Discrepancy Text</label>
              <textarea id="form-text" required rows={3} className="halite-input mt-1 w-full" value={form.discrepancy} onChange={e => setForm({...form, discrepancy: e.target.value})}></textarea>
            </div>

            <Button type="submit" loading={formSubmitting}>
              {formSubmitting ? 'Processing...' : 'Submit Record'}
            </Button>
          </form>

          {formError && (
            <p role="alert" className="mt-4 rounded-md bg-red-500/10 px-3 py-2 font-sans text-sm text-red-400">
              {formError}
            </p>
          )}

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
