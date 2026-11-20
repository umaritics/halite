import api from '../../api/client';

const readOptions = (signal) => ({ timeout: 15000, signal });
const idPath = (id) => `/sessions/${encodeURIComponent(id)}`;

// Reuse the shared authenticated instance, including single-flight JWT refresh.
export const sessionsAPI = {
  assets: (signal) => api.get('/maintenance/assets', readOptions(signal)),
  list: (params = {}, signal) => api.get('/sessions', { params, ...readOptions(signal) }),
  get: (id, signal) => api.get(idPath(id), readOptions(signal)),
  create: (payload) => api.post('/sessions', payload, { timeout: 15000 }),
  turn: (id, payload) => api.post(`${idPath(id)}/turns`, payload, { timeout: 300000 }),
  close: (id, payload) => api.post(`${idPath(id)}/close`, payload, { timeout: 15000 }),
  report: (id) => api.get(`${idPath(id)}/report`, { timeout: 15000, responseType: 'text' }),
  experiments: (signal) => api.get('/sessions/experiments', readOptions(signal)),
  summary: (signal) => api.get('/sessions/summary', readOptions(signal)),
  diagnose: (assetId, symptomText) => api.post('/maintenance/diagnose', {
    asset_id: assetId, symptom_text: symptomText, allow_degraded: true,
  }, { timeout: 300000 }),
};
