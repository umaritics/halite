import api from '../../api/http';

export const authAPI = {
  login: (email, password) => api.post('/auth/login', { email, password }),
  refresh: (refreshToken) =>
    api.post('/auth/refresh', refreshToken ? { refresh_token: refreshToken } : {}),
  logout: (refreshToken) =>
    api.post('/auth/logout', refreshToken ? { refresh_token: refreshToken } : {}),
  me: () => api.get('/auth/me'),
  changePassword: (currentPassword, newPassword) =>
    api.post('/auth/password', {
      current_password: currentPassword,
      new_password: newPassword,
    }),
  verifyInvite: (token) => api.get('/auth/invites/verify', { params: { token } }),
  acceptInvite: ({ token, password, fullName }) =>
    api.post('/auth/invites/accept', {
      token,
      password,
      full_name: fullName || undefined,
    }),
};
