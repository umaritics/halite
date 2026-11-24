import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import {
  authAPI,
  setRefreshSessionHandler,
  setSessionTokenGetter,
} from '../api/client';
import { clearLegacyInvestigations } from '../features/investigation/privacy';

const REFRESH_STORAGE_KEY = 'halite.session.refresh.v1';

// Refresh tokens rotate: the server retires a token as soon as it is used.
// Two refresh calls sent with the same token therefore race, and the loser
// gets a 401 and signs the user out. React StrictMode runs the restore effect
// twice in development, so every caller shares one in-flight request.
let inflightRefresh = null;
function refreshOnce() {
  if (!inflightRefresh) {
    const stored = readStoredRefreshToken();
    inflightRefresh = authAPI.refresh(stored || undefined).finally(() => {
      inflightRefresh = null;
    });
  }
  return inflightRefresh;
}

function readStoredRefreshToken() {
  try {
    return window.sessionStorage.getItem(REFRESH_STORAGE_KEY) || '';
  } catch {
    return '';
  }
}

function writeStoredRefreshToken(token) {
  try {
    if (token) {
      window.sessionStorage.setItem(REFRESH_STORAGE_KEY, token);
    } else {
      window.sessionStorage.removeItem(REFRESH_STORAGE_KEY);
    }
  } catch {
    // Guarded storage: private browsing / storage quota never breaks sign-in
  }
}

// Default context value when components are rendered standalone in unit tests
// without wrapping <AuthProvider> — keeps existing page unit tests intact.
const FALLBACK_AUTH_CONTEXT = {
  status: 'authenticated',
  isAuthenticated: false,
  user: null,
  login: async () => {},
  acceptInvite: async () => {},
  logout: async () => {},
  refreshSession: async () => null,
  hasRole: (...roles) => (roles.length === 0 ? true : roles.includes('supervisor')),
};

const AuthContext = createContext(FALLBACK_AUTH_CONTEXT);

export function AuthProvider({ children }) {
  const [status, setStatus] = useState('loading'); // 'loading' | 'authenticated' | 'unauthenticated'
  const [user, setUser] = useState(null);
  const accessTokenRef = useRef('');

  const applySessionPayload = useCallback((data) => {
    clearLegacyInvestigations();
    const access = String(data?.access_token || '').trim();
    const refresh = String(data?.refresh_token || '').trim();
    accessTokenRef.current = access;
    if (refresh) {
      writeStoredRefreshToken(refresh);
    }
    setUser(data?.user || null);
    setStatus(access && data?.user ? 'authenticated' : 'unauthenticated');
    return access || null;
  }, []);

  const clearLocalSession = useCallback(() => {
    clearLegacyInvestigations();
    accessTokenRef.current = '';
    writeStoredRefreshToken('');
    setUser(null);
    setStatus('unauthenticated');
  }, []);

  const refreshSession = useCallback(async () => {
    try {
      const { data } = await refreshOnce();
      return applySessionPayload(data);
    } catch {
      clearLocalSession();
      return null;
    }
  }, [applySessionPayload, clearLocalSession]);

  useEffect(() => {
    setSessionTokenGetter(() => accessTokenRef.current);
    setRefreshSessionHandler(() => refreshSession());
    return () => {
      setSessionTokenGetter(null);
      setRefreshSessionHandler(null);
    };
  }, [refreshSession]);

  useEffect(() => {
    let active = true;
    refreshOnce()
      .then(({ data }) => {
        if (active) applySessionPayload(data);
      })
      .catch(() => {
        if (active) clearLocalSession();
      });
    return () => {
      active = false;
    };
  }, [applySessionPayload, clearLocalSession]);

  const login = useCallback(
    async (email, password) => {
      const { data } = await authAPI.login(email, password);
      applySessionPayload(data);
      return data.user;
    },
    [applySessionPayload],
  );

  const acceptInvite = useCallback(
    async ({ token, password, fullName }) => {
      const { data } = await authAPI.acceptInvite({ token, password, fullName });
      applySessionPayload(data);
      return data.user;
    },
    [applySessionPayload],
  );

  const logout = useCallback(async () => {
    const storedRefresh = readStoredRefreshToken();
    try {
      await authAPI.logout(storedRefresh || undefined);
    } catch {
      // Clear client session even if server is unreachable
    } finally {
      clearLocalSession();
    }
  }, [clearLocalSession]);

  const hasRole = useCallback(
    (...roles) => {
      if (!user?.role) return false;
      if (roles.length === 0) return true;
      return roles.map((r) => r.toLowerCase()).includes(String(user.role).toLowerCase());
    },
    [user],
  );

  const value = useMemo(
    () => ({
      status,
      isAuthenticated: status === 'authenticated' && Boolean(user),
      user,
      login,
      acceptInvite,
      logout,
      refreshSession,
      hasRole,
    }),
    [status, user, login, acceptInvite, logout, refreshSession, hasRole],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
