import api from '../../api/http';

// getRecord re-runs the conflict engine, so it can reach a language model and gets a long
// timeout. The review screen no longer uses it; it stays only because the shared client
// still exposes it.
const MODEL_TIMEOUT_MS = 300000;

export const integrityAPI = {
  getRecord: (id) => api.get(`/maintenance/records/${id}`, { timeout: MODEL_TIMEOUT_MS }),
  // The stored proposal for one queued record. Reads the graph only; no model is called.
  proposal: (id) => api.get(`/maintenance/review-queue/${id}/proposal`),
  reviewQueue: () => api.get('/maintenance/review-queue'),
  analysisStatus: () => api.get('/maintenance/analysis/status'),
  corrections: (params) => api.get('/maintenance/corrections', { params }),
  accept: (recordId, note) => api.post(`/maintenance/review-queue/${recordId}/accept`, { note }),
  reject: (recordId, note) => api.post(`/maintenance/review-queue/${recordId}/reject`, { note }),
};
