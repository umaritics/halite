import axios from 'axios';

let sessionTokenGetter = null;
let refreshSessionHandler = null;
let inflightRefreshPromise = null;

/**
 * Register a runtime token provider so user Access JWTs take precedence
 * over any build-time fallback API key.
 */
export function setSessionTokenGetter(getter) {
  sessionTokenGetter = typeof getter === 'function' ? getter : null;
}

/**
 * Register an async handler `() => Promise<string | null>` invoked once on
 * unexpected 401 responses to rotate the refresh session transparently.
 */
export function setRefreshSessionHandler(handler) {
  refreshSessionHandler = typeof handler === 'function' ? handler : null;
}

export function resolveClientBearerToken(envKey = import.meta.env.VITE_HALITE_API_KEY) {
  const sessionToken = sessionTokenGetter ? String(sessionTokenGetter() || '').trim() : '';
  if (sessionToken) return sessionToken;
  return String(envKey || '').trim();
}

export function applyAuthHeaders(config, envKey = import.meta.env.VITE_HALITE_API_KEY) {
  const next = { ...config, headers: { ...(config?.headers || {}) } };
  const hasAuth = Object.keys(next.headers).some((k) => k.toLowerCase() === 'authorization');
  if (!hasAuth) {
    const token = resolveClientBearerToken(envKey);
    if (token) {
      next.headers.Authorization = `Bearer ${token}`;
    }
  }
  return next;
}

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => applyAuthHeaders(config));

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalConfig = error?.config;
    const status = error?.response?.status;
    const url = String(originalConfig?.url || '');
    const isAuthHandshake =
      url.includes('/auth/login') ||
      url.includes('/auth/refresh') ||
      url.includes('/auth/logout') ||
      url.includes('/auth/invites/');

    if (
      status === 401 &&
      refreshSessionHandler &&
      originalConfig &&
      !originalConfig._haliteRetried &&
      !isAuthHandshake
    ) {
      originalConfig._haliteRetried = true;
      try {
        if (!inflightRefreshPromise) {
          inflightRefreshPromise = Promise.resolve(refreshSessionHandler()).finally(() => {
            inflightRefreshPromise = null;
          });
        }
        const nextAccessToken = await inflightRefreshPromise;
        if (nextAccessToken) {
          originalConfig.headers = {
            ...(originalConfig.headers || {}),
            Authorization: `Bearer ${nextAccessToken}`,
          };
          return api.request(originalConfig);
        }
      } catch {
        // Refresh failed; propagate original 401 so AuthContext / UI can respond
      }
    }
    return Promise.reject(error);
  },
);

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

export const adminAPI = {
  listUsers: () => api.get('/admin/users'),
  updateUser: (userId, updates) => api.patch(`/admin/users/${userId}`, updates),
  listInvites: () => api.get('/admin/invites'),
  createInvite: (payload) => api.post('/admin/invites', payload),
  revokeInvite: (inviteId) => api.delete(`/admin/invites/${inviteId}`),
  auditEvents: (params) => api.get('/admin/audit-events', { params }),
};

export const graphAPI = {
  // `limit` is the maximum number of nodes returned; the backend default is only 200.
  overview: (limit) => api.get('/graph/overview', limit ? { params: { limit } } : undefined),
};

export const healthAPI = {
  check: () => api.get('/health'),
};

export const maintenanceAPI = {
  ingest: (payload) => api.post('/maintenance/ingest', payload),
  // Multipart CSV upload (field name `file`); `ingest` above takes a server-side csv_path instead.
  ingestFile: (formData) => api.post('/maintenance/ingest/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
  submitRecord: (payload) => api.post('/maintenance/records', payload),
  records: (params) => api.get('/maintenance/records', { params }),
  getRecord: (id) => api.get(`/maintenance/records/${id}`),
  assets: (params) => api.get('/maintenance/assets', { params }),
  assetHistory: (assetId) => api.get(`/maintenance/assets/${assetId}/history`),
  reviewQueue: () => api.get('/maintenance/review-queue'),
  analysisStatus: () => api.get('/maintenance/analysis/status'),
  corrections: (params) => api.get('/maintenance/corrections', { params }),
  accept: (recordId, note) => api.post(`/maintenance/review-queue/${recordId}/accept`, { note }),
  reject: (recordId, note) => api.post(`/maintenance/review-queue/${recordId}/reject`, { note }),
};

export default api;
