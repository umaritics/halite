import api from '../../api/http';

export const graphAPI = {
  // `limit` is the maximum number of nodes returned; the backend default is only 200.
  // Up to 3,000 nodes from a CPU-only staging server: allow longer than the 30 s default.
  overview: (limit) =>
    api.get('/graph/overview', { timeout: 120000, ...(limit ? { params: { limit } } : {}) }),
};
