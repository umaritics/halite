import api from '../../api/http';

export const assetsAPI = {
  records: (params) => api.get('/maintenance/records', { params }),
  assets: (params) => api.get('/maintenance/assets', { params }),
  assetHistory: (assetId) => api.get(`/maintenance/assets/${assetId}/history`),
};
