// Shared error helpers. Kept free of React so they can be unit tested.

// FastAPI returns `detail` as a string for HTTPException but as an array of
// {loc, msg, type} objects for request-validation (422) errors. Rendering the
// array directly would crash the page, so always flatten to text here.
export function formatDetail(detail) {
  if (detail == null) return null;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    const parts = detail
      .map((d) => {
        if (typeof d === 'string') return d;
        if (d && typeof d.msg === 'string') {
          const field = Array.isArray(d.loc) ? d.loc[d.loc.length - 1] : null;
          return field ? `${field}: ${d.msg}` : d.msg;
        }
        return null;
      })
      .filter(Boolean);
    return parts.length ? parts.join('; ') : null;
  }
  return null;
}

export const TIMEOUT_MESSAGE = 'The server took too long to respond. Try again.';
export const SIGNED_OUT_MESSAGE = 'You are signed out or your session expired. Sign in again.';

// Classify a failed GET so a page can say what actually went wrong instead of
// showing an "empty" state (which would wrongly imply there is no data).
export function describeLoadError(err) {
  const status = err?.response?.status;
  const detail = formatDetail(err?.response?.data?.detail);

  const isNetwork =
    !err?.response &&
    (err?.code === 'ERR_NETWORK' || Boolean(err?.request) || /network/i.test(err?.message || ''));

  if (err?.code === 'ECONNABORTED') {
    return { kind: 'timeout', message: TIMEOUT_MESSAGE };
  }
  if (isNetwork) {
    return {
      kind: 'network',
      message: 'The backend did not respond. Check that the API server is running.',
    };
  }
  if (status === 401 || status === 403) {
    return {
      kind: 'unauthorized',
      message: detail || SIGNED_OUT_MESSAGE,
    };
  }
  if (status === 404) {
    return { kind: 'not-found', message: detail || 'Not found.' };
  }
  if (status === 429) {
    return {
      kind: 'rate-limited',
      message: detail || 'Too many requests. Wait a moment and try again.',
    };
  }
  if (status === 503) {
    return {
      kind: 'unavailable',
      message: detail || 'A required service (database or model) is unavailable.',
    };
  }
  if (status >= 500) {
    return { kind: 'server', message: `The backend failed while handling this request (HTTP ${status}).` };
  }
  return { kind: 'unknown', message: detail || err?.message || 'Something went wrong.' };
}
