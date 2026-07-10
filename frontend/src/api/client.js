import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  headers: { 'Content-Type': 'application/json' },
});

export const chatAPI = {
  send: (message, history) => api.post('/chat', { message, conversation_history: history }),
};

export const decisionsAPI = {
  list: (params) => api.get('/decisions', { params }),
  create: (data) => api.post('/decisions', data),
  get: (id) => api.get(`/decisions/${id}`),
  update: (id, data) => api.patch(`/decisions/${id}`, data),
  delete: (id) => api.delete(`/decisions/${id}`),
  invalidate: (id, note) => api.post(`/decisions/${id}/invalidate`, { note }),
};

export const graphAPI = {
  overview: () => api.get('/graph/overview'),
  component: (id) => api.get(`/graph/component/${id}`),
  decision: (id) => api.get(`/graph/decision/${id}`),
};

export const ingestAPI = {
  document: (formData) =>
    api.post('/ingest/document', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  gitea: (owner, repo) => api.post('/ingest/gitea', { owner, repo }),
  code: (owner, repo) => api.post('/ingest/code', { owner, repo }),
};

export const alertsAPI = {
  list: () => api.get('/alerts'),
  acknowledge: (id) => api.post(`/alerts/${id}/acknowledge`),
};

export const healthAPI = {
  check: () => api.get('/health'),
};

export default api;
