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
  timeout: 30000,
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

export default api;
