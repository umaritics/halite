import api from '../../api/http';

export const graphAPI = {
  // `limit` is the maximum number of nodes returned; the backend default is only 200.
  overview: (limit) => api.get('/graph/overview', limit ? { params: { limit } } : undefined),
};
