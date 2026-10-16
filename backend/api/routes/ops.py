"""
Ops endpoints for the shared staging backend.

Partners do not need VM SSH. They can:
  - GET /api/ops/version  (public) — which SHA is live
  - GET /api/ops/logs     (OPS_TOKEN) — recent application log lines
"""
from __future__ import annotations

import logging
import os
import re
import secrets
import time
from collections import deque
from typing import Deque

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from api.deps import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ops", tags=["ops"])

_SECRET_RE = re.compile(
    r"(?i)(api[_-]?key|password|token|secret|authorization)\s*[:=]\s*([^\s,;]+)"
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
    return _SECRET_RE.sub(r"\1=[REDACTED]", line)


def _require_ops_token(
    x_ops_token: str | None = Header(default=None, alias="X-Ops-Token"),
    settings=Depends(get_settings),
) -> None:
    expected = (getattr(settings, "OPS_TOKEN", None) or "").strip()
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="OPS_TOKEN is not configured on this server. Ask the deploy admin to set it.",
        )
    supplied = (x_ops_token or "").strip()
    if not supplied or not secrets.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing X-Ops-Token")


@router.get("/version")
def ops_version(settings=Depends(get_settings)):
    """Public: which build is serving traffic."""
    return {
        "app": "Halite",
        "git_sha": os.environ.get("GIT_SHA") or getattr(settings, "GIT_SHA", "unknown"),
        "deployed_at": os.environ.get("DEPLOYED_AT") or getattr(settings, "DEPLOYED_AT", ""),
        "demo_mode": settings.DEMO_MODE,
        "neo4j_configured": settings.neo4j_configured,
        "groq_configured": settings.groq_configured,
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
