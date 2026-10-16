// Helpers for the Diagnostics page. Kept free of React so they can be unit tested.

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

// Turn a failed diagnose request into something a technician can act on.
// Never invents a diagnosis; always says what failed and what to do next.
export function describeDiagnosticError(err) {
  const status = err?.response?.status;
  const detail = formatDetail(err?.response?.data?.detail);

  const isNetwork =
    !err?.response &&
    (err?.code === 'ERR_NETWORK' || Boolean(err?.request) || /network/i.test(err?.message || ''));

  if (isNetwork) {
    return {
      kind: 'network',
      title: 'Cannot reach the Halite API',
      message: 'The backend did not respond. Check that the API server is running, then try again.',
      detail: null,
      retryable: true,
    };
  }

  switch (status) {
    case 400:
    case 422:
      return {
        kind: 'validation',
        title: 'Check the request',
        message: 'The diagnostic request was rejected as invalid.',
        detail,
        retryable: false,
      };
    case 404:
      return {
        kind: 'no-history',
        title: 'No service history for this aircraft',
        message:
          'This aircraft has no records in the loaded corpus, so Halite has nothing to reason from. Pick a different aircraft.',
        detail: null,
        retryable: false,
      };
    case 503:
      return {
        kind: 'model-unavailable',
        title: 'Diagnostic model unavailable',
        message:
          'The live language model is not available right now. Halite does not substitute a made-up answer, so no diagnosis is shown.',
        detail,
        retryable: true,
      };
    case 429:
      return {
        kind: 'rate-limited',
        title: 'Model rate limit reached',
        message: 'The model service is limiting requests. Wait a moment, then try again.',
        detail,
        retryable: true,
      };
    default:
      if (status >= 500) {
        return {
          kind: 'server-error',
          title: 'The diagnostic service hit an error',
          message: `The backend failed while handling this request (HTTP ${status}). This can happen when the model call fails. Try again in a moment.`,
          detail,
          retryable: true,
        };
      }
      return {
        kind: 'unknown',
        title: 'Diagnostic failed',
        message: detail || err?.message || 'Something went wrong while running the diagnostic.',
        detail: null,
        retryable: false,
      };
  }
}

// The backend asks the model for JSON {explanation, rare_cases, warnings}. When it
// cannot parse the reply it falls back to returning the raw text as the explanation,
// which would show up on screen as a JSON blob. Recover the readable text if so.
export function extractExplanation(raw) {
  if (typeof raw !== 'string') return { text: '', warnings: [], recovered: false };

  const cleaned = raw
    .trim()
    .replace(/^```[a-z]*\s*/i, '')
    .replace(/```\s*$/, '')
    .trim();

  if (!cleaned.startsWith('{')) return { text: raw, warnings: [], recovered: false };

  try {
    const obj = JSON.parse(cleaned);
    if (obj && typeof obj.explanation === 'string') {
      return {
        text: obj.explanation,
        warnings: Array.isArray(obj.warnings) ? obj.warnings.filter((w) => typeof w === 'string') : [],
        recovered: true,
      };
    }
  } catch {
    // fall through: truncated or otherwise invalid JSON
  }

  const match = cleaned.match(/"explanation"\s*:\s*"((?:[^"\\]|\\[\s\S])*)/);
  if (match) {
    let text = match[1];
    try {
      text = JSON.parse(`"${text}"`);
    } catch {
      text = text.replace(/\\n/g, '\n').replace(/\\"/g, '"').replace(/\\\\/g, '\\');
    }
    return { text, warnings: [], recovered: true };
  }

  return { text: raw, warnings: [], recovered: false };
}

// The backend replaces any cited record ID it cannot find in the graph with a marker such as
// "[UNVERIFIED:SWIA2025000000000]" (see docs/mid1/12_u4_u5_diagnostics_handoff.md). Split text
// into plain and flagged segments so the UI can style the markers as warnings.
const UNVERIFIED_MARKER = /(\[UNVERIFIED(?::[^\]]*)?\])/g;

export function splitUnverified(text) {
  if (typeof text !== 'string' || text === '') return [];
  return text
    .split(UNVERIFIED_MARKER)
    .filter((part) => part !== '')
    .map((part) => ({ text: part, flagged: /^\[UNVERIFIED(?::[^\]]*)?\]$/.test(part) }));
}
