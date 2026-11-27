import api from '../../api/http';

export const adminAPI = {
  listUsers: () => api.get('/admin/users'),
  updateUser: (userId, updates) => api.patch(`/admin/users/${userId}`, updates),
  listInvites: () => api.get('/admin/invites'),
  createInvite: (payload) => api.post('/admin/invites', payload),
  revokeInvite: (inviteId) => api.delete(`/admin/invites/${inviteId}`),
  auditEvents: (params) => api.get('/admin/audit-events', { params }),
};

export const healthAPI = {
  check: () => api.get('/health'),
};
