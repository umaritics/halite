"""
Application-layer security controls for Halite API.

Defense-in-depth layers implemented here:
  1. Primary client authentication (`HALITE_API_KEY`) via `Authorization: Bearer <key>`
     (primary) or `X-Halite-Api-Key: <key>` (alias), compared in constant time.
     Fails closed (HTTP 503) if `DEMO_MODE=false` and `HALITE_API_KEY` is unset.
  2. Privileged operator token (`OPS_TOKEN`) via `X-Ops-Token` for destructive or
     sensitive operational routes (`/api/ops/logs`, `DELETE /api/graph/reset`,
     `POST /api/maintenance/analysis/run`). Valid `OPS_TOKEN` also satisfies standard
     API authentication so operators do not have to pass redundant headers.
  3. Bounded in-memory sliding-window rate limiting per client IP (general API,
     LLM/model quota routes, and authentication failure brute-force throttling),
     trusting `X-Forwarded-For` only from loopback reverse proxies (Caddy).
  4. ASGI response security headers (`nosniff`, `DENY` framing, `no-store` cache
     policy on `/api/*`, `noindex`).
"""
from __future__ import annotations

import logging
import math
import secrets
import threading
import time
from collections import deque
from typing import Deque

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from api.deps import get_settings

logger = logging.getLogger(__name__)

_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost", "testclient"})

bearer_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="HaliteBearerAuth",
    description="Primary client API key (`Authorization: Bearer <HALITE_API_KEY>`).",
)
api_key_header_scheme = APIKeyHeader(
    name="X-Halite-Api-Key",
    auto_error=False,
    scheme_name="HaliteApiKeyHeader",
    description="Alias header carrying `<HALITE_API_KEY>`.",
)
ops_token_header_scheme = APIKeyHeader(
    name="X-Ops-Token",
    auto_error=False,
    scheme_name="HaliteOpsToken",
    description="Privileged operator secret (`OPS_TOKEN`) for ops and destructive endpoints.",
)


def constant_time_equals(supplied: str | None, expected: str | None) -> bool:
    """Compare two non-empty secret strings using `secrets.compare_digest`."""
    lhs = (supplied or "").strip()
    rhs = (expected or "").strip()
    if not lhs or not rhs:
        return False
    return secrets.compare_digest(lhs.encode("utf-8"), rhs.encode("utf-8"))


def get_client_ip(request: Request) -> str:
    """
    Resolve client IP safely behind a localhost reverse proxy (Caddy on 127.0.0.1).

    Only trusts `X-Forwarded-For` when the immediate TCP peer is loopback, and
    reads the rightmost hop appended by the local reverse proxy so internet
    callers cannot spoof upstream `X-Forwarded-For` entries to evade limits.
    """
    peer = (request.client.host if request.client else "") or "unknown"
    if peer in _LOOPBACK_HOSTS:
        xff = request.headers.get("x-forwarded-for", "")
        if xff:
            rightmost = xff.split(",")[-1].strip()
            if rightmost:
                return rightmost
    return peer


class SlidingWindowRateLimiter:
    """Bounded thread-safe in-memory sliding-window rate limiter."""

    def __init__(self, max_buckets: int = 4096):
        self._max_buckets = max_buckets
        self._lock = threading.Lock()
        self._events: dict[tuple[str, str], Deque[float]] = {}

    def check_and_record(
        self,
        scope: str,
        subject: str,
        limit: int,
        window_seconds: float = 60.0,
    ) -> tuple[bool, int]:
        """Return `(allowed, retry_after_seconds)`."""
        if limit <= 0:
            return True, 0

        now = time.monotonic()
        cutoff = now - window_seconds
        key = (scope, subject)

        with self._lock:
            bucket = self._events.get(key)
            if bucket is None:
                if len(self._events) >= self._max_buckets:
                    self._evict_stale_locked(cutoff)
                bucket = deque()
                self._events[key] = bucket

            while bucket and bucket[0] <= cutoff:
                bucket.popleft()

            if len(bucket) >= limit:
                retry_after = max(1, int(math.ceil(bucket[0] + window_seconds - now)))
                return False, retry_after

            bucket.append(now)
            return True, 0

    def is_limited(
        self,
        scope: str,
        subject: str,
        limit: int,
        window_seconds: float = 60.0,
    ) -> tuple[bool, int]:
        """Inspect whether `(scope, subject)` has already reached `limit` without adding an event."""
        if limit <= 0:
            return False, 0

        now = time.monotonic()
        cutoff = now - window_seconds
        key = (scope, subject)

        with self._lock:
            bucket = self._events.get(key)
            if not bucket:
                return False, 0
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                retry_after = max(1, int(math.ceil(bucket[0] + window_seconds - now)))
                return True, retry_after
            return False, 0

    def _evict_stale_locked(self, cutoff: float) -> None:
        stale_keys = [
            key for key, bucket in self._events.items()
            if not bucket or bucket[-1] <= cutoff
        ]
        for key in stale_keys:
            self._events.pop(key, None)
        if len(self._events) >= self._max_buckets:
            # Drop oldest inserted key to keep memory strictly bounded
            oldest_key = next(iter(self._events))
            self._events.pop(oldest_key, None)


def _get_limiter(request: Request) -> SlidingWindowRateLimiter:
    limiter = getattr(request.app.state, "rate_limiter", None)
    if limiter is None:
        limiter = SlidingWindowRateLimiter()
        request.app.state.rate_limiter = limiter
    return limiter


def _enforce_rate_limit(
    request: Request,
    settings,
    *,
    scope: str,
    limit_attr: str,
    default_limit: int,
    detail: str,
) -> None:
    if not getattr(settings, "RATE_LIMIT_ENABLED", True):
        return
    limit = int(getattr(settings, limit_attr, default_limit))
    if limit <= 0:
        return
    client_ip = get_client_ip(request)
    allowed, retry_after = _get_limiter(request).check_and_record(
        scope, client_ip, limit, window_seconds=60.0
    )
    if not allowed:
        logger.warning(
            "Rate limit exceeded scope=%s client_ip=%s path=%s",
            scope,
            client_ip,
            request.url.path,
        )
        raise HTTPException(
            status_code=429,
            detail=detail,
            headers={"Retry-After": str(retry_after)},
        )


def _check_auth_lockout(request: Request, settings, client_ip: str) -> None:
    if not getattr(settings, "RATE_LIMIT_ENABLED", True):
        return
    limit = int(getattr(settings, "RATE_LIMIT_AUTH_FAILURES_PER_MINUTE", 20))
    limited, retry_after = _get_limiter(request).is_limited(
        "auth_fail", client_ip, limit, window_seconds=60.0
    )
    if limited:
        raise HTTPException(
            status_code=429,
            detail="Too many failed authentication attempts. Wait and retry.",
            headers={"Retry-After": str(retry_after)},
        )


def _record_auth_failure(request: Request, settings, client_ip: str) -> None:
    if not getattr(settings, "RATE_LIMIT_ENABLED", True):
        return
    limit = int(getattr(settings, "RATE_LIMIT_AUTH_FAILURES_PER_MINUTE", 20))
    allowed, retry_after = _get_limiter(request).check_and_record(
        "auth_fail", client_ip, limit, window_seconds=60.0
    )
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Too many failed authentication attempts. Wait and retry.",
            headers={"Retry-After": str(retry_after)},
        )


def _extract_bearer_or_header_key(
    request: Request,
    bearer: HTTPAuthorizationCredentials | None,
    x_halite_api_key: str | None,
) -> str:
    if bearer and bearer.scheme.lower() == "bearer" and bearer.credentials:
        return bearer.credentials.strip()

    # Handle raw Authorization header if scheme casing or whitespace differed
    raw_auth = (request.headers.get("authorization") or "").strip()
    if raw_auth.lower().startswith("bearer "):
        return raw_auth[7:].strip()

    if x_halite_api_key:
        return x_halite_api_key.strip()

    return ""


def require_halite_api_key(
    request: Request,
    bearer: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
    x_halite_api_key: str | None = Security(api_key_header_scheme),
    x_ops_token: str | None = Security(ops_token_header_scheme),
    settings=Depends(get_settings),
) -> None:
    """
    Enforce application-layer API authentication on protected `/api/*` routes.

    - When `DEMO_MODE=false` and `HALITE_API_KEY` is unset: fail closed with 503.
    - When `HALITE_API_KEY` is set (or `DEMO_MODE=false`): require a valid
      `Authorization: Bearer <HALITE_API_KEY>`, `X-Halite-Api-Key: <HALITE_API_KEY>`,
      or privileged `X-Ops-Token: <OPS_TOKEN>`.
    - When `DEMO_MODE=true` and `HALITE_API_KEY` is empty: allow local/test calls.
    """
    expected_api_key = (getattr(settings, "HALITE_API_KEY", None) or "").strip()
    expected_ops_token = (getattr(settings, "OPS_TOKEN", None) or "").strip()
    demo_mode = bool(getattr(settings, "DEMO_MODE", True))

    if not demo_mode and not expected_api_key:
        logger.error(
            "Refusing request to %s: DEMO_MODE=false but HALITE_API_KEY is unset",
            request.url.path,
        )
        raise HTTPException(
            status_code=503,
            detail=(
                "API authentication is required on non-demo deployments, "
                "but HALITE_API_KEY is not configured on this server."
            ),
        )

    auth_required = bool(expected_api_key) or not demo_mode
    client_ip = get_client_ip(request)

    if auth_required:
        _check_auth_lockout(request, settings, client_ip)

        supplied_key = _extract_bearer_or_header_key(request, bearer, x_halite_api_key)
        valid_api_key = constant_time_equals(supplied_key, expected_api_key)
        valid_ops_token = constant_time_equals(x_ops_token, expected_ops_token)

        if not (valid_api_key or valid_ops_token):
            _record_auth_failure(request, settings, client_ip)
            logger.warning(
                "Rejected unauthenticated request method=%s path=%s client_ip=%s",
                request.method,
                request.url.path,
                client_ip,
            )
            raise HTTPException(
                status_code=401,
                detail="Invalid or missing API key. Supply Authorization: Bearer <key>.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    _enforce_rate_limit(
        request,
        settings,
        scope="api",
        limit_attr="RATE_LIMIT_API_PER_MINUTE",
        default_limit=180,
        detail="API rate limit exceeded. Slow down and retry shortly.",
    )


def require_ops_token(
    request: Request,
    x_ops_token: str | None = Security(ops_token_header_scheme),
    settings=Depends(get_settings),
) -> None:
    """Enforce privileged `OPS_TOKEN` via `X-Ops-Token` (fail-closed 503 when unset)."""
    expected = (getattr(settings, "OPS_TOKEN", None) or "").strip()
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="OPS_TOKEN is not configured on this server. Ask the deploy admin to set it.",
        )

    client_ip = get_client_ip(request)
    _check_auth_lockout(request, settings, client_ip)

    if not constant_time_equals(x_ops_token, expected):
        _record_auth_failure(request, settings, client_ip)
        logger.warning(
            "Rejected ops request method=%s path=%s client_ip=%s",
            request.method,
            request.url.path,
            client_ip,
        )
        raise HTTPException(status_code=401, detail="Invalid or missing X-Ops-Token")


def require_llm_rate_limit(
    request: Request,
    settings=Depends(get_settings),
) -> None:
    """Protect external LLM/Groq quota on model-backed routes."""
    _enforce_rate_limit(
        request,
        settings,
        scope="llm",
        limit_attr="RATE_LIMIT_LLM_PER_MINUTE",
        default_limit=20,
        detail="Model request rate limit exceeded. Wait before sending more diagnostic/chat requests.",
    )


def require_public_rate_limit(
    request: Request,
    settings=Depends(get_settings),
) -> None:
    """Prevent anonymous scanners from flooding public health/version routes."""
    _enforce_rate_limit(
        request,
        settings,
        scope="public",
        limit_attr="RATE_LIMIT_API_PER_MINUTE",
        default_limit=180,
        detail="Rate limit exceeded.",
    )


class SecurityHeadersMiddleware:
    """Pure ASGI middleware adding hardened HTTP response headers."""

    _STATIC_HEADERS = (
        (b"x-content-type-options", b"nosniff"),
        (b"x-frame-options", b"DENY"),
        (b"referrer-policy", b"no-referrer"),
        (b"x-robots-tag", b"noindex, nofollow"),
        (b"permissions-policy", b"geolocation=(), microphone=(), camera=()"),
    )

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path: str = scope.get("path", "")

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                raw_headers = list(message.get("headers", []))
                existing = {name.lower() for name, _ in raw_headers}
                for header_name, header_val in self._STATIC_HEADERS:
                    if header_name not in existing:
                        raw_headers.append((header_name, header_val))
                if path.startswith("/api") and b"cache-control" not in existing:
                    raw_headers.append((b"cache-control", b"no-store"))
                message = {**message, "headers": raw_headers}
            await send(message)

        await self.app(scope, receive, send_with_headers)
