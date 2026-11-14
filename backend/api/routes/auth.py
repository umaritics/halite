"""
Authentication (`/api/auth/*`) and Workspace Administration (`/api/admin/*`) routes.

Implements Halite Module M01 (Workspace & Identity — FYP-I Final):
  - Invite-only onboarding (prevents public bot registration & LLM quota abuse)
  - Argon2id password verification + per-account lockout
  - Short-lived HS256 Access JWT + rotating single-use Refresh Sessions (`HttpOnly` cookie + JSON fallback)
  - Role-Based Access Control (`technician`, `supervisor`, `admin`)
  - Immutable security & governance audit log (`audit_events`)
"""
from __future__ import annotations

import json
import logging
from typing import Literal

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import select

from api.deps import get_rel_store, get_settings
from api.security import (
    AuthPrincipal,
    get_client_ip,
    require_auth_endpoint_rate_limit,
    require_roles,
    require_user_principal,
)
from db.models import AuditEvent, Organization, User, UserInvite
from services.auth_service import (
    AuthError,
    accept_user_invite,
    authenticate_user,
    count_active_admins,
    create_user_invite,
    ensure_default_organization,
    hash_password,
    inspect_invite_token,
    record_audit_event,
    revoke_all_user_sessions,
    revoke_session_by_refresh_token,
    rotate_refresh_session,
    serialize_user,
    validate_role,
    verify_password,
)

logger = logging.getLogger(__name__)

REFRESH_COOKIE_NAME = "halite_refresh"

# Public auth endpoints (mounted outside `require_halite_api_key` with dedicated rate limit)
public_auth_router = APIRouter(
    prefix="/auth",
    tags=["auth"],
    dependencies=[Depends(require_auth_endpoint_rate_limit)],
)

# Signed-in user account endpoints
protected_auth_router = APIRouter(prefix="/auth", tags=["auth"])

# Admin governance endpoints (`role == "admin"` only)
admin_router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_roles("admin"))],
)


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str | None = None


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


class AcceptInviteRequest(BaseModel):
    token: str = Field(min_length=16, max_length=256)
    password: str = Field(min_length=10, max_length=128)
    full_name: str | None = Field(default=None, max_length=160)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=10, max_length=128)


class CreateInviteRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    full_name: str = Field(min_length=1, max_length=160)
    role: Literal["technician", "supervisor", "admin"] = "technician"
    expires_in_hours: int = Field(default=72, ge=1, le=336)


class UpdateUserRequest(BaseModel):
    role: Literal["technician", "supervisor", "admin"] | None = None
    is_active: bool | None = None
    full_name: str | None = Field(default=None, min_length=1, max_length=160)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_rel_store(rel_store):
    if rel_store is None or not rel_store.is_available:
        raise HTTPException(
            status_code=503,
            detail="Authentication database is not configured on this server (set DATABASE_URL).",
        )
    return rel_store


def _set_refresh_cookie(response: Response, raw_token: str, settings, request: Request) -> None:
    is_https = (
        request.url.scheme == "https"
        or request.headers.get("x-forwarded-proto", "").lower() == "https"
        or not bool(getattr(settings, "DEMO_MODE", True))
    )
    max_age = max(1, int(getattr(settings, "JWT_REFRESH_TTL_DAYS", 7))) * 86400
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=raw_token,
        max_age=max_age,
        httponly=True,
        secure=is_https,
        samesite="none" if is_https else "lax",
        path="/",
    )


def _clear_refresh_cookie(response: Response, settings, request: Request) -> None:
    is_https = (
        request.url.scheme == "https"
        or request.headers.get("x-forwarded-proto", "").lower() == "https"
        or not bool(getattr(settings, "DEMO_MODE", True))
    )
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        httponly=True,
        secure=is_https,
        samesite="none" if is_https else "lax",
        path="/",
    )


# ---------------------------------------------------------------------------
# Public /api/auth/* endpoints
# ---------------------------------------------------------------------------

@public_auth_router.post("/login")
def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    settings=Depends(get_settings),
    rel_store=Depends(get_rel_store),
):
    store = _require_rel_store(rel_store)
    client_ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "")

    # Note: failed logins commit their audit/lockout counters even when raising 401/429
    with store.session_scope() as db:
        try:
            result = authenticate_user(
                db,
                settings,
                email=body.email,
                password=body.password,
                ip_address=client_ip,
                user_agent=user_agent,
            )
        except AuthError as err:
            db.commit()
            raise HTTPException(status_code=err.status_code, detail=err.detail) from err

    _set_refresh_cookie(response, result["refresh_token"], settings, request)
    return result


@public_auth_router.post("/refresh")
def refresh_session(
    request: Request,
    response: Response,
    body: RefreshRequest | None = None,
    cookie_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
    settings=Depends(get_settings),
    rel_store=Depends(get_rel_store),
):
    store = _require_rel_store(rel_store)
    raw_token = ((body.refresh_token if body else None) or cookie_token or "").strip()
    if not raw_token:
        raise HTTPException(status_code=401, detail="No active refresh session found.")

    client_ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "")

    with store.session_scope() as db:
        try:
            result = rotate_refresh_session(
                db,
                settings,
                raw_refresh_token=raw_token,
                ip_address=client_ip,
                user_agent=user_agent,
            )
        except AuthError as err:
            db.commit()
            _clear_refresh_cookie(response, settings, request)
            raise HTTPException(status_code=err.status_code, detail=err.detail) from err

    _set_refresh_cookie(response, result["refresh_token"], settings, request)
    return result


@public_auth_router.post("/logout")
def logout(
    request: Request,
    response: Response,
    body: LogoutRequest | None = None,
    cookie_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
    settings=Depends(get_settings),
    rel_store=Depends(get_rel_store),
):
    if rel_store is not None and rel_store.is_available:
        raw_token = ((body.refresh_token if body else None) or cookie_token or "").strip()
        if raw_token:
            with rel_store.session_scope() as db:
                revoke_session_by_refresh_token(db, raw_token)
    _clear_refresh_cookie(response, settings, request)
    return {"logged_out": True}


@public_auth_router.get("/invites/verify")
def verify_invite(
    token: str = Query(min_length=16, max_length=256),
    rel_store=Depends(get_rel_store),
):
    store = _require_rel_store(rel_store)
    with store.session_scope() as db:
        try:
            return inspect_invite_token(db, token)
        except AuthError as err:
            raise HTTPException(status_code=err.status_code, detail=err.detail) from err


@public_auth_router.post("/invites/accept")
def accept_invite(
    body: AcceptInviteRequest,
    request: Request,
    response: Response,
    settings=Depends(get_settings),
    rel_store=Depends(get_rel_store),
):
    store = _require_rel_store(rel_store)
    client_ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "")

    with store.session_scope() as db:
        try:
            result = accept_user_invite(
                db,
                settings,
                raw_token=body.token,
                password=body.password,
                full_name=body.full_name,
                ip_address=client_ip,
                user_agent=user_agent,
            )
        except AuthError as err:
            raise HTTPException(status_code=err.status_code, detail=err.detail) from err

    _set_refresh_cookie(response, result["refresh_token"], settings, request)
    return result


# ---------------------------------------------------------------------------
# Authenticated /api/auth/* endpoints
# ---------------------------------------------------------------------------

@protected_auth_router.get("/me")
def current_user_profile(
    principal: AuthPrincipal = Depends(require_user_principal),
    rel_store=Depends(get_rel_store),
):
    store = _require_rel_store(rel_store)
    with store.session_scope() as db:
        user = db.get(User, principal.user_id)
        if user is None or not user.is_active:
            raise HTTPException(status_code=401, detail="User account is inactive.")
        org = db.get(Organization, user.organization_id)
        return serialize_user(user, org)


@protected_auth_router.post("/password")
def change_password(
    body: ChangePasswordRequest,
    request: Request,
    principal: AuthPrincipal = Depends(require_user_principal),
    rel_store=Depends(get_rel_store),
):
    store = _require_rel_store(rel_store)
    client_ip = get_client_ip(request)
    with store.session_scope() as db:
        user = db.get(User, principal.user_id)
        if user is None or not user.is_active:
            raise HTTPException(status_code=401, detail="User account is inactive.")
        ok, _ = verify_password(body.current_password, user.password_hash)
        if not ok:
            raise HTTPException(status_code=400, detail="Current password is incorrect.")
        try:
            user.password_hash = hash_password(body.new_password)
        except AuthError as err:
            raise HTTPException(status_code=err.status_code, detail=err.detail) from err

        revoked_others = revoke_all_user_sessions(
            db, user.id, except_session_id=principal.session_id
        )
        record_audit_event(
            db,
            action="auth.password.changed",
            organization_id=user.organization_id,
            actor_user_id=user.id,
            actor_email=user.email,
            actor_role=user.role,
            target_type="user",
            target_id=user.id,
            metadata={"revoked_other_sessions": revoked_others},
            ip_address=client_ip,
        )
    return {"password_changed": True, "revoked_other_sessions": revoked_others}


# ---------------------------------------------------------------------------
# Admin /api/admin/* governance endpoints
# ---------------------------------------------------------------------------

@admin_router.get("/users")
def list_workspace_users(
    principal: AuthPrincipal = Depends(require_roles("admin")),
    rel_store=Depends(get_rel_store),
):
    store = _require_rel_store(rel_store)
    with store.session_scope() as db:
        stmt = select(User).order_by(User.created_at.asc())
        if principal.organization_id:
            stmt = stmt.where(User.organization_id == principal.organization_id)
        users = db.scalars(stmt).all()
        orgs = {o.id: o for o in db.scalars(select(Organization)).all()}
        return [serialize_user(u, orgs.get(u.organization_id)) for u in users]


@admin_router.patch("/users/{user_id}")
def update_workspace_user(
    user_id: str,
    body: UpdateUserRequest,
    request: Request,
    principal: AuthPrincipal = Depends(require_roles("admin")),
    rel_store=Depends(get_rel_store),
):
    store = _require_rel_store(rel_store)
    client_ip = get_client_ip(request)
    with store.session_scope() as db:
        user = db.get(User, user_id)
        if user is None or (
            principal.organization_id and user.organization_id != principal.organization_id
        ):
            raise HTTPException(status_code=404, detail="User not found.")

        removing_admin = (
            user.role == "admin"
            and user.is_active
            and (
                (body.role is not None and body.role != "admin")
                or (body.is_active is False)
            )
        )
        if removing_admin:
            if user.id == principal.user_id:
                raise HTTPException(
                    status_code=400,
                    detail="You cannot deactivate or demote your own administrator account.",
                )
            if count_active_admins(db, user.organization_id) <= 1:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot remove the last active administrator in the workspace.",
                )

        changes: dict[str, object] = {}
        revoke_sessions = False

        if body.role is not None and body.role != user.role:
            changes["previous_role"] = user.role
            user.role = validate_role(body.role)
            changes["new_role"] = user.role
            revoke_sessions = True

        if body.is_active is not None and body.is_active != user.is_active:
            user.is_active = body.is_active
            changes["is_active"] = body.is_active
            if not body.is_active:
                revoke_sessions = True

        if body.full_name is not None:
            cleaned_name = body.full_name.strip()
            if cleaned_name and cleaned_name != user.full_name:
                user.full_name = cleaned_name
                changes["full_name"] = cleaned_name

        if revoke_sessions:
            changes["sessions_revoked"] = revoke_all_user_sessions(db, user.id)

        if changes:
            record_audit_event(
                db,
                action="auth.user.updated",
                organization_id=user.organization_id,
                actor_user_id=principal.user_id,
                actor_email=principal.email,
                actor_role=principal.role,
                target_type="user",
                target_id=user.id,
                metadata=changes,
                ip_address=client_ip,
            )

        org = db.get(Organization, user.organization_id)
        return serialize_user(user, org)


@admin_router.get("/invites")
def list_workspace_invites(
    principal: AuthPrincipal = Depends(require_roles("admin")),
    rel_store=Depends(get_rel_store),
):
    store = _require_rel_store(rel_store)
    with store.session_scope() as db:
        stmt = select(UserInvite).order_by(UserInvite.created_at.desc()).limit(100)
        if principal.organization_id:
            stmt = stmt.where(UserInvite.organization_id == principal.organization_id)
        rows = db.scalars(stmt).all()
        return [
            {
                "id": inv.id,
                "email": inv.email,
                "full_name": inv.full_name,
                "role": inv.role,
                "expires_at": inv.expires_at.isoformat() if inv.expires_at else None,
                "accepted_at": inv.accepted_at.isoformat() if inv.accepted_at else None,
                "revoked_at": inv.revoked_at.isoformat() if inv.revoked_at else None,
                "created_at": inv.created_at.isoformat() if inv.created_at else None,
            }
            for inv in rows
        ]


@admin_router.post("/invites", status_code=201)
def issue_workspace_invite(
    body: CreateInviteRequest,
    request: Request,
    principal: AuthPrincipal = Depends(require_roles("admin")),
    settings=Depends(get_settings),
    rel_store=Depends(get_rel_store),
):
    store = _require_rel_store(rel_store)
    client_ip = get_client_ip(request)
    with store.session_scope() as db:
        org_id = principal.organization_id
        if not org_id:
            org = ensure_default_organization(db, settings)
            org_id = org.id
        try:
            invite, raw_token = create_user_invite(
                db,
                organization_id=org_id,
                email=body.email,
                full_name=body.full_name,
                role=body.role,
                invited_by_user_id=principal.user_id if principal.kind == "user" else None,
                expires_in_hours=body.expires_in_hours,
                ip_address=client_ip,
            )
        except AuthError as err:
            raise HTTPException(status_code=err.status_code, detail=err.detail) from err

        invite_path = f"/accept-invite?token={raw_token}"
        frontend_base = (getattr(settings, "FRONTEND_URL", "") or "").rstrip("/")
        return {
            "invite": {
                "id": invite.id,
                "email": invite.email,
                "full_name": invite.full_name,
                "role": invite.role,
                "expires_at": invite.expires_at.isoformat(),
            },
            "invite_token": raw_token,
            "invite_path": invite_path,
            "invite_url": f"{frontend_base}{invite_path}" if frontend_base else invite_path,
        }


@admin_router.delete("/invites/{invite_id}")
def revoke_workspace_invite(
    invite_id: str,
    request: Request,
    principal: AuthPrincipal = Depends(require_roles("admin")),
    rel_store=Depends(get_rel_store),
):
    from services.auth_service import utc_now

    store = _require_rel_store(rel_store)
    client_ip = get_client_ip(request)
    with store.session_scope() as db:
        invite = db.get(UserInvite, invite_id)
        if invite is None or (
            principal.organization_id and invite.organization_id != principal.organization_id
        ):
            raise HTTPException(status_code=404, detail="Invite not found.")
        if invite.accepted_at is not None:
            raise HTTPException(status_code=409, detail="Invite has already been accepted.")
        invite.revoked_at = utc_now()
        record_audit_event(
            db,
            action="auth.invite.revoked",
            organization_id=invite.organization_id,
            actor_user_id=principal.user_id,
            actor_email=principal.email,
            actor_role=principal.role,
            target_type="invite",
            target_id=invite.id,
            metadata={"invited_email": invite.email},
            ip_address=client_ip,
        )
    return {"revoked": True, "id": invite_id}


@admin_router.get("/audit-events")
def list_audit_events(
    limit: int = Query(default=50, ge=1, le=200),
    action: str | None = Query(default=None),
    principal: AuthPrincipal = Depends(require_roles("admin")),
    rel_store=Depends(get_rel_store),
):
    store = _require_rel_store(rel_store)
    with store.session_scope() as db:
        stmt = select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(limit)
        if action:
            stmt = stmt.where(AuditEvent.action == action)
        rows = db.scalars(stmt).all()
        items = []
        for ev in rows:
            meta = None
            if ev.metadata_json:
                try:
                    meta = json.loads(ev.metadata_json)
                except ValueError:
                    meta = {"raw": ev.metadata_json}
            items.append(
                {
                    "id": ev.id,
                    "action": ev.action,
                    "actor_user_id": ev.actor_user_id,
                    "actor_email": ev.actor_email,
                    "actor_role": ev.actor_role,
                    "target_type": ev.target_type,
                    "target_id": ev.target_id,
                    "metadata": meta,
                    "ip_address": ev.ip_address,
                    "created_at": ev.created_at.isoformat() if ev.created_at else None,
                }
            )
        return {"items": items, "count": len(items)}
