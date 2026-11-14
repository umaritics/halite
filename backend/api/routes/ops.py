"""
Ops endpoints for the shared staging backend.

Partners do not need VM SSH. They can:
  - GET /api/ops/version  (public) — which SHA is live + non-secret runtime flags
  - GET /api/ops/logs     (OPS_TOKEN) — recent redacted application log lines
"""
from __future__ import annotations

import logging
import os
import re
import time
from collections import deque
from typing import Deque

from fastapi import APIRouter, Depends, Query

from api.deps import get_settings
from api.security import require_ops_token, require_public_rate_limit

logger = logging.getLogger(__name__)

# Mounted without API key in api/router.py
public_router = APIRouter(prefix="/ops", tags=["ops"])
# Mounted under authenticated /api router + privileged X-Ops-Token guard
router = APIRouter(prefix="/ops", tags=["ops"])

# Backward-compatible export used by graph.py, maintenance.py, and tests
_require_ops_token = require_ops_token

_SECRET_KV_RE = re.compile(
    r"(?i)(halite[_-]?api[_-]?key|ops[_-]?token|groq[_-]?api[_-]?key(?:[_-]?fallback)?|"
    r"neo4j[_-]?password|jwt[_-]?secret[_-]?key|bootstrap[_-]?admin[_-]?password|"
    r"refresh[_-]?token|invite[_-]?token|gitea[_-]?(?:token|webhook[_-]?secret)|"
    r"x-halite-api-key|x-ops-token|api[_-]?key|password|token|secret|authorization)"
    r"\s*([:=])\s*(?:bearer\s+)?([^\s,;\"']+)"
)
_BEARER_RE = re.compile(r"(?i)\b(bearer)\s+([A-Za-z0-9._~+/=-]{8,})")
_URI_CRED_RE = re.compile(
    r"(?i)\b((?:bolt|neo4j|postgres|postgresql)(?:\+[a-z0-9]+)?://[^:\s/@]+:)([^@\s]+)(@)"
)


class RingBufferHandler(logging.Handler):
    """In-process ring buffer so /ops/logs works without SSH or Docker access."""

    def __init__(self, capacity: int = 3000):
        super().__init__()
        self.buffer: Deque[str] = deque(maxlen=capacity)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.buffer.append(self.format(record))
        except Exception:
            self.handleError(record)


_ring = RingBufferHandler(capacity=3000)
_ring.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
_installed = False


def install_ring_buffer_logging() -> None:
    global _installed
    if _installed:
        return
    logging.getLogger().addHandler(_ring)
    _installed = True
    logger.info("Ops ring-buffer logging installed")


def _redact(line: str) -> str:
    scrubbed = _URI_CRED_RE.sub(r"\1[REDACTED]\3", line)
    scrubbed = _BEARER_RE.sub(r"\1 [REDACTED]", scrubbed)
    scrubbed = _SECRET_KV_RE.sub(r"\1\2[REDACTED]", scrubbed)
    return scrubbed


@public_router.get("/version", dependencies=[Depends(require_public_rate_limit)])
def ops_version(settings=Depends(get_settings)):
    """Public: which build is serving traffic (build/mode metadata only, no secrets)."""
    return {
        "app": "Halite",
        "git_sha": os.environ.get("GIT_SHA") or getattr(settings, "GIT_SHA", "unknown"),
        "deployed_at": os.environ.get("DEPLOYED_AT") or getattr(settings, "DEPLOYED_AT", ""),
        "demo_mode": settings.DEMO_MODE,
        "neo4j_configured": settings.neo4j_configured,
        "groq_configured": settings.groq_configured,
        "auth_enabled": bool(getattr(settings, "api_auth_required", not settings.DEMO_MODE)),
        "openapi_enabled": bool(getattr(settings, "openapi_enabled", settings.DEMO_MODE)),
        "ops_logs_enabled": bool((getattr(settings, "OPS_TOKEN", None) or "").strip()),
        "server_time_unix": int(time.time()),
    }


@router.get("/logs")
def ops_logs(
    lines: int = Query(default=200, ge=1, le=2000),
    _: None = Depends(_require_ops_token),
):
    """Recent application logs (ring buffer). Requires header X-Ops-Token."""
    raw = list(_ring.buffer)[-lines:]
    return {
        "count": len(raw),
        "lines": [_redact(line) for line in raw],
    }
