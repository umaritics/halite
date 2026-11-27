import api from '../../api/http';

const INGEST_TIMEOUT_MS = 120000;
const MODEL_TIMEOUT_MS = 300000;

export const intakeAPI = {
  ingest: (payload) => api.post('/maintenance/ingest', payload, { timeout: INGEST_TIMEOUT_MS }),
  // Multipart CSV upload (field name `file`); `ingest` above takes a server-side csv_path instead.
  ingestFile: (formData) =>
    api.post('/maintenance/ingest/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: INGEST_TIMEOUT_MS,
    }),
  submitRecord: (payload) =>
    api.post('/maintenance/records', payload, { timeout: MODEL_TIMEOUT_MS }),
};
