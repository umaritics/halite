import api from '../../api/http';

// getRecord can reach a language model, so it gets a long timeout.
const MODEL_TIMEOUT_MS = 300000;

export const integrityAPI = {
  getRecord: (id) => api.get(`/maintenance/records/${id}`, { timeout: MODEL_TIMEOUT_MS }),
  reviewQueue: () => api.get('/maintenance/review-queue'),
  analysisStatus: () => api.get('/maintenance/analysis/status'),
  corrections: (params) => api.get('/maintenance/corrections', { params }),
  accept: (recordId, note) => api.post(`/maintenance/review-queue/${recordId}/accept`, { note }),
  reject: (recordId, note) => api.post(`/maintenance/review-queue/${recordId}/reject`, { note }),
};
