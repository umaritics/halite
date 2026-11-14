"""
Application-layer authentication, RBAC authorization, rate limiting, and
security headers for Halite API.

Authentication tiers supported by `require_halite_api_key` / `get_current_principal`:
  1. **Website User Access JWT** (`Authorization: Bearer <jwt>`):
     Signed `HS256` token issued by `/api/auth/login`, `/api/auth/refresh`, or
     `/api/auth/invites/accept`. Verified cryptographically AND checked against
     the active `User` + `UserSession` row in PostgreSQL/SQLite so session logout,
     role changes, or account deactivation take effect immediately.
  2. **Server-to-Server API Key** (`Authorization: Bearer <HALITE_API_KEY>` or
     `X-Halite-Api-Key: <HALITE_API_KEY>`):
     Constant-time `secrets.compare_digest` check for CI smoke scripts and trusted
     backend integrations (never needed in public browser bundles once user login is used).
  3. **Privileged Operator Token** (`X-Ops-Token: <OPS_TOKEN>`):
     Required for destructive/ops endpoints (`/api/ops/logs`, `DELETE /api/graph/reset`).
  4. **Local Demo/Unit-Test Fallback** (`DEMO_MODE=true` with `HALITE_API_KEY=""`
     and no `Authorization` header):
     Attaches a deterministic `demo` principal so offline unit tests run without boilerplate,
     while any explicit JWT or configured `HALITE_API_KEY` enforces full auth & RBAC.
"""
from __future__ import annotations

import logging
import math
import secrets
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Callable, Deque, Literal

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from api.deps import get_rel_store, get_settings

logger = logging.getLogger(__name__)

_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost", "testclient"})

bearer_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="HaliteBearerAuth",
    description="User Access JWT (`Authorization: Bearer <jwt>`) or server `HALITE_API_KEY`.",
)
api_key_header_scheme = APIKeyHeader(
    name="X-Halite-Api-Key",
    auto_error=False,
    scheme_name="HaliteApiKeyHeader",
    description="Server-to-server alias header carrying `<HALITE_API_KEY>`.",
)
ops_token_header_scheme = APIKeyHeader(
    name="X-Ops-Token",
    auto_error=False,
    scheme_name="HaliteOpsToken",
    description="Privileged operator secret (`OPS_TOKEN`) for ops and destructive endpoints.",
)


@dataclass(frozen=True)
class AuthPrincipal:
    kind: Literal["user", "api_key", "ops_token", "demo"]
    user_id: str | None
    email: str | None
    full_name: str
    role: str  # "technician" | "supervisor" | "admin"
    organization_id: str | None = None
    session_id: str | None = None


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


def _extract_bearer_token(
    request: Request,
    bearer: HTTPAuthorizationCredentials | None,
) -> str:
    if bearer and bearer.scheme.lower() == "bearer" and bearer.credentials:
        return bearer.credentials.strip()
    raw_auth = (request.headers.get("authorization") or "").strip()
    if raw_auth.lower().startswith("bearer "):
        return raw_auth[7:].strip()
    return ""


def _looks_like_jwt(token: str) -> bool:
    return token.count(".") == 2 and token.startswith("eyJ")


def _verify_user_jwt_principal(token: str, settings, rel_store) -> AuthPrincipal:
    from db.models import User, UserSession
    from services.auth_service import AuthError, decode_access_jwt

    try:
        claims = decode_access_jwt(token, settings)
    except AuthError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.detail,
            headers={"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None,
        ) from exc

    user_id = str(claims.get("sub") or "")
    session_id = str(claims.get("sid") or "")

    # Verify active user & non-revoked session in relational store when available
    if rel_store is not None and rel_store.is_available:
        with rel_store.session_scope() as db:
            user = db.get(User, user_id)
            if user is None or not user.is_active:
                raise HTTPException(
                    status_code=401,
                    detail="User account is inactive or no longer exists.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            session_row = db.get(UserSession, session_id)
            if session_row is None or session_row.revoked_at is not None:
                raise HTTPException(
                    status_code=401,
                    detail="Session has been signed out or revoked. Please sign in again.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return AuthPrincipal(
                kind="user",
                user_id=user.id,
                email=user.email,
                full_name=user.full_name,
                role=user.role,
                organization_id=user.organization_id,
                session_id=session_row.id,
            )

    return AuthPrincipal(
        kind="user",
        user_id=user_id,
        email=str(claims.get("email") or ""),
        full_name=str(claims.get("name") or "User"),
        role=str(claims.get("role") or "technician"),
        organization_id=str(claims.get("org_id") or "") or None,
        session_id=session_id,
    )


def require_halite_api_key(
    request: Request,
    bearer: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
    x_halite_api_key: str | None = Security(api_key_header_scheme),
    x_ops_token: str | None = Security(ops_token_header_scheme),
    settings=Depends(get_settings),
    rel_store=Depends(get_rel_store),
) -> AuthPrincipal:
    """
    Enforce authentication on protected `/api/*` routes and populate `request.state.principal`.

    Accepts:
      - User Access JWT (`Authorization: Bearer <jwt>`)
      - Server `HALITE_API_KEY` (`Authorization: Bearer <key>` or `X-Halite-Api-Key`)
      - Privileged `OPS_TOKEN` (`X-Ops-Token`)
    Fails closed (`503`) if `DEMO_MODE=false` and neither `HALITE_API_KEY` nor user JWT auth
    is configured (`jwt_secret_strong` + `rel_store`).
    """
    cached = getattr(request.state, "principal", None)
    if isinstance(cached, AuthPrincipal):
        return cached

    expected_api_key = (getattr(settings, "HALITE_API_KEY", None) or "").strip()
    expected_ops_token = (getattr(settings, "OPS_TOKEN", None) or "").strip()
    demo_mode = bool(getattr(settings, "DEMO_MODE", True))
    user_jwt_ready = bool(
        getattr(settings, "jwt_secret_strong", False)
        and rel_store is not None
        and rel_store.is_available
    )

    if not demo_mode and not expected_api_key and not user_jwt_ready:
        logger.error(
            "Refusing request to %s: DEMO_MODE=false without HALITE_API_KEY or configured auth DB",
            request.url.path,
        )
        raise HTTPException(
            status_code=503,
            detail=(
                "API authentication is required on non-demo deployments, "
                "but HALITE_API_KEY is not configured on this server."
            ),
        )

    client_ip = get_client_ip(request)
    bearer_token = _extract_bearer_token(request, bearer)
    supplied_header_key = (x_halite_api_key or "").strip()
    has_any_credential = bool(bearer_token or supplied_header_key or (x_ops_token or "").strip())

    principal: AuthPrincipal | None = None

    # 1. User Access JWT path
    if bearer_token and _looks_like_jwt(bearer_token):
        _check_auth_lockout(request, settings, client_ip)
        try:
            principal = _verify_user_jwt_principal(bearer_token, settings, rel_store)
        except HTTPException as exc:
            if exc.status_code == 401:
                _record_auth_failure(request, settings, client_ip)
            raise

    # 2. Server-to-server static API key or privileged OPS_TOKEN path
    elif has_any_credential or not demo_mode or bool(expected_api_key):
        _check_auth_lockout(request, settings, client_ip)
        candidate_key = bearer_token or supplied_header_key
        supplied_ops = (x_ops_token or "").strip()
        if supplied_ops and not candidate_key and not expected_ops_token:
            raise HTTPException(
                status_code=503,
                detail="OPS_TOKEN is not configured on this server. Ask the deploy admin to set it.",
            )
        if constant_time_equals(candidate_key, expected_api_key):
            principal = AuthPrincipal(
                kind="api_key",
                user_id="service:api-key",
                email=None,
                full_name="Halite Service Key",
                role="supervisor",
            )
        elif constant_time_equals(x_ops_token, expected_ops_token):
            principal = AuthPrincipal(
                kind="ops_token",
                user_id="service:ops-token",
                email=None,
                full_name="Halite Operations Token",
                role="admin",
            )
        else:
            _record_auth_failure(request, settings, client_ip)
            logger.warning(
                "Rejected unauthenticated request method=%s path=%s client_ip=%s",
                request.method,
                request.url.path,
                client_ip,
            )
            raise HTTPException(
                status_code=401,
                detail="Authentication required. Sign in or supply a valid Bearer token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # 3. Demo/unit-test default principal when DEMO_MODE=true and no credentials configured/sent
    else:
        principal = AuthPrincipal(
            kind="demo",
            user_id="demo-user",
            email="demo@halite.local",
            full_name="Demo Workspace User",
            role="admin",
        )

    _enforce_rate_limit(
        request,
        settings,
        scope="api",
        limit_attr="RATE_LIMIT_API_PER_MINUTE",
        default_limit=180,
        detail="API rate limit exceeded. Slow down and retry shortly.",
    )

    request.state.principal = principal
    return principal


def get_current_principal(
    principal: AuthPrincipal = Depends(require_halite_api_key),
) -> AuthPrincipal:
    return principal


def require_user_principal(
    principal: AuthPrincipal = Depends(require_halite_api_key),
) -> AuthPrincipal:
    """Require an interactive signed-in user JWT (rejects static API keys)."""
    if principal.kind != "user":
        raise HTTPException(
            status_code=401,
            detail="A signed-in user session is required for this endpoint.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return principal


def require_roles(*allowed_roles: str) -> Callable[..., AuthPrincipal]:
    allowed = frozenset(r.lower() for r in allowed_roles)

    def _dependency(principal: AuthPrincipal = Depends(require_halite_api_key)) -> AuthPrincipal:
        if principal.role.lower() not in allowed:
            roles_display = ", ".join(sorted(allowed))
            raise HTTPException(
                status_code=403,
                detail=(
                    f"Insufficient permissions: role '{principal.role}' cannot perform this action "
                    f"(requires: {roles_display})."
                ),
            )
        return principal

    return _dependency


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


def require_ops_or_admin(
    request: Request,
    bearer: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
    x_ops_token: str | None = Security(ops_token_header_scheme),
    settings=Depends(get_settings),
    rel_store=Depends(get_rel_store),
) -> None:
    """
    Allow either `X-Ops-Token` OR an authenticated `admin` user JWT.

    Preserves 503 behavior when `OPS_TOKEN` is unset and no `admin` JWT is supplied.
    """
    bearer_token = _extract_bearer_token(request, bearer)
    if bearer_token and _looks_like_jwt(bearer_token):
        principal = _verify_user_jwt_principal(bearer_token, settings, rel_store)
        if principal.role != "admin":
            raise HTTPException(
                status_code=403,
                detail="Administrator role is required to run batch conflict analysis.",
            )
        request.state.principal = principal
        return

    require_ops_token(request=request, x_ops_token=x_ops_token, settings=settings)


def require_auth_endpoint_rate_limit(
    request: Request,
    settings=Depends(get_settings),
) -> None:
    """Tight rate limit on login / token-refresh / invite acceptance endpoints."""
    client_ip = get_client_ip(request)
    _check_auth_lockout(request, settings, client_ip)
    _enforce_rate_limit(
        request,
        settings,
        scope="auth_endpoint",
        limit_attr="RATE_LIMIT_AUTH_FAILURES_PER_MINUTE",
        default_limit=20,
        detail="Too many authentication requests. Wait a moment and try again.",
    )


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
