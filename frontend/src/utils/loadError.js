import { formatDetail } from './diagnostics';

// Classify a failed GET so a page can say what actually went wrong instead of
// showing an "empty" state (which would wrongly imply there is no data).
export function describeLoadError(err) {
  const status = err?.response?.status;
  const detail = formatDetail(err?.response?.data?.detail);

  const isNetwork =
    !err?.response &&
    (err?.code === 'ERR_NETWORK' || Boolean(err?.request) || /network/i.test(err?.message || ''));

  if (isNetwork) {
    return {
      kind: 'network',
      message: 'The backend did not respond. Check that the API server is running.',
    };
  }
  if (status === 404) {
    return { kind: 'not-found', message: detail || 'Not found.' };
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
