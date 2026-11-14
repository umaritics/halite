"""
Authentication, Password Hashing (Argon2id), JWT Access Tokens, Rotating Refresh
Token Families, Invite-Only Provisioning, and Audit Event Service.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from db.models import (
    VALID_ROLES,
    AuditEvent,
    Organization,
    User,
    UserInvite,
    UserSession,
)

logger = logging.getLogger(__name__)

JWT_ISSUER = "halite-api"
JWT_AUDIENCE = "halite-web"
JWT_ALGORITHM = "HS256"

# OWASP / RFC 9106 balanced interactive Argon2id profile
_ph = PasswordHasher(time_cost=2, memory_cost=65536, parallelism=2)
# Precomputed dummy Argon2id hash so non-existent emails pay identical CPU cost (no timing oracle)
_DUMMY_ARGON2_HASH = _ph.hash("halite-constant-time-dummy-password-placeholder")

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class AuthError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def normalize_email(email: str) -> str:
    cleaned = (email or "").strip().lower()
    if not cleaned or len(cleaned) > 254 or not _EMAIL_RE.match(cleaned):
        raise AuthError(422, "Provide a valid email address.")
    return cleaned


def validate_password_strength(password: str) -> None:
    if not isinstance(password, str) or len(password) < 10:
        raise AuthError(422, "Password must be at least 10 characters long.")
    if len(password) > 128:
        raise AuthError(422, "Password must not exceed 128 characters.")
    has_letter = any(ch.isalpha() for ch in password)
    has_digit = any(ch.isdigit() for ch in password)
    if not (has_letter and has_digit):
        raise AuthError(422, "Password must include at least one letter and one number.")


def validate_role(role: str) -> str:
    cleaned = (role or "").strip().lower()
    if cleaned not in VALID_ROLES:
        raise AuthError(422, f"Role must be one of: {', '.join(VALID_ROLES)}.")
    return cleaned


def hash_password(password: str) -> str:
    validate_password_strength(password)
    return _ph.hash(password)


def verify_password(password: str, password_hash: str) -> tuple[bool, bool]:
    """Return `(valid, needs_rehash)`."""
    try:
        _ph.verify(password_hash, password)
        return True, _ph.check_needs_rehash(password_hash)
    except (VerifyMismatchError, InvalidHashError):
        return False, False


def hash_opaque_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def ensure_jwt_secret(settings) -> str:
    demo_mode = bool(getattr(settings, "DEMO_MODE", True))
    secret = (getattr(settings, "effective_jwt_secret", "") or "").strip()
    if not demo_mode and not getattr(settings, "jwt_secret_strong", False):
        raise AuthError(
            503,
            "JWT signing secret is not securely configured on this server (set SECRET_KEY or JWT_SECRET_KEY >= 32 chars).",
        )
    return secret or "halite-demo-jwt-secret-for-unit-tests-only-32b"


def issue_access_jwt(user: User, session_id: str, settings) -> tuple[str, int]:
    secret = ensure_jwt_secret(settings)
    ttl_minutes = max(1, int(getattr(settings, "JWT_ACCESS_TTL_MINUTES", 15)))
    expires_in = ttl_minutes * 60
    now = utc_now()
    payload = {
        "sub": user.id,
        "email": user.email,
        "name": user.full_name,
        "role": user.role,
        "org_id": user.organization_id,
        "sid": session_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_in)).timestamp()),
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
    }
    token = jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)
    return token, expires_in


def decode_access_jwt(token: str, settings) -> dict[str, Any]:
    secret = ensure_jwt_secret(settings)
    try:
        return jwt.decode(
            token,
            secret,
            algorithms=[JWT_ALGORITHM],
            issuer=JWT_ISSUER,
            audience=JWT_AUDIENCE,
            options={"require": ["sub", "sid", "role", "exp", "iat"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise AuthError(401, "Session access token has expired. Refresh or sign in again.") from exc
    except jwt.PyJWTError as exc:
        raise AuthError(401, "Invalid authentication token.") from exc


def serialize_user(user: User, org: Organization | None = None) -> dict[str, Any]:
    organization = org or user.organization
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": user.is_active,
        "organization_id": user.organization_id,
        "organization": (
            {
                "id": organization.id,
                "slug": organization.slug,
                "name": organization.name,
            }
            if organization
            else None
        ),
        "last_login_at": _as_utc(user.last_login_at).isoformat() if user.last_login_at else None,
        "created_at": _as_utc(user.created_at).isoformat() if user.created_at else None,
    }


def record_audit_event(
    db: Session,
    *,
    action: str,
    organization_id: str | None = None,
    actor_user_id: str | None = None,
    actor_email: str | None = None,
    actor_role: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> AuditEvent:
    event = AuditEvent(
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        actor_email=actor_email,
        actor_role=actor_role,
        action=action,
        target_type=target_type,
        target_id=target_id,
        metadata_json=json.dumps(metadata, ensure_ascii=False) if metadata else None,
        ip_address=ip_address,
    )
    db.add(event)
    return event


def ensure_default_organization(db: Session, settings) -> Organization:
    slug = (getattr(settings, "BOOTSTRAP_ORG_SLUG", "halite-ops") or "halite-ops").strip().lower()
    name = (
        getattr(settings, "BOOTSTRAP_ORG_NAME", "Halite Maintenance Operations")
        or "Halite Maintenance Operations"
    ).strip()
    org = db.scalar(select(Organization).where(Organization.slug == slug))
    if org is None:
        org = Organization(slug=slug, name=name, is_active=True)
        db.add(org)
        db.flush()
    return org


def bootstrap_admin_if_configured(rel_store, settings) -> dict[str, Any] | None:
    """Idempotently provision initial admin account when BOOTSTRAP_ADMIN_* env vars are set."""
    if not rel_store or not rel_store.is_available:
        return None
    raw_email = (getattr(settings, "BOOTSTRAP_ADMIN_EMAIL", "") or "").strip()
    raw_password = getattr(settings, "BOOTSTRAP_ADMIN_PASSWORD", "") or ""
    full_name = (
        getattr(settings, "BOOTSTRAP_ADMIN_NAME", "Halite Administrator")
        or "Halite Administrator"
    ).strip()
    if not raw_email or not raw_password:
        return None

    email = normalize_email(raw_email)
    with rel_store.session_scope() as db:
        org = ensure_default_organization(db, settings)
        existing = db.scalar(select(User).where(User.email == email))
        if existing is not None:
            return serialize_user(existing, org)

        user = User(
            organization_id=org.id,
            email=email,
            full_name=full_name,
            password_hash=hash_password(raw_password),
            role="admin",
            is_active=True,
        )
        db.add(user)
        db.flush()
        record_audit_event(
            db,
            action="auth.admin.bootstrapped",
            organization_id=org.id,
            actor_user_id=user.id,
            actor_email=user.email,
            actor_role="admin",
            target_type="user",
            target_id=user.id,
            metadata={"source": "startup_bootstrap"},
        )
        logger.info("Bootstrapped initial Halite admin user: %s", email)
        return serialize_user(user, org)


def _create_refresh_session(
    db: Session,
    user: User,
    settings,
    *,
    ip_address: str | None = None,
    user_agent: str | None = None,
    family_id: str | None = None,
) -> tuple[UserSession, str]:
    raw_refresh = secrets.token_urlsafe(48)
    ttl_days = max(1, int(getattr(settings, "JWT_REFRESH_TTL_DAYS", 7)))
    sess = UserSession(
        user_id=user.id,
        family_id=family_id or str(uuid.uuid4()),
        token_hash=hash_opaque_token(raw_refresh),
        ip_address=(ip_address or "")[:64] or None,
        user_agent=(user_agent or "")[:512] or None,
        expires_at=utc_now() + timedelta(days=ttl_days),
    )
    db.add(sess)
    db.flush()
    return sess, raw_refresh


def authenticate_user(
    db: Session,
    settings,
    *,
    email: str,
    password: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    cleaned_email = normalize_email(email)
    user = db.scalar(select(User).where(User.email == cleaned_email))
    now = utc_now()

    if user is None:
        # Constant-time Argon2 work so attackers cannot enumerate registered emails
        verify_password(password or "", _DUMMY_ARGON2_HASH)
        record_audit_event(
            db,
            action="auth.login.failed",
            actor_email=cleaned_email,
            metadata={"reason": "unknown_email"},
            ip_address=ip_address,
        )
        raise AuthError(401, "Invalid email or password.")

    locked_until = _as_utc(user.locked_until)
    if locked_until and locked_until > now:
        remaining_min = max(1, int((locked_until - now).total_seconds() // 60) + 1)
        record_audit_event(
            db,
            action="auth.login.locked",
            organization_id=user.organization_id,
            actor_user_id=user.id,
            actor_email=user.email,
            actor_role=user.role,
            ip_address=ip_address,
        )
        raise AuthError(
            429,
            f"Account is temporarily locked after repeated failed attempts. Try again in {remaining_min} minute(s).",
        )

    valid_pw, needs_rehash = verify_password(password or "", user.password_hash)
    if not valid_pw:
        user.failed_login_count = (user.failed_login_count or 0) + 1
        max_attempts = max(3, int(getattr(settings, "AUTH_MAX_FAILED_ATTEMPTS", 5)))
        if user.failed_login_count >= max_attempts:
            lock_mins = max(1, int(getattr(settings, "AUTH_LOCKOUT_MINUTES", 15)))
            user.locked_until = now + timedelta(minutes=lock_mins)
        record_audit_event(
            db,
            action="auth.login.failed",
            organization_id=user.organization_id,
            actor_user_id=user.id,
            actor_email=user.email,
            actor_role=user.role,
            metadata={"failed_login_count": user.failed_login_count},
            ip_address=ip_address,
        )
        db.flush()
        raise AuthError(401, "Invalid email or password.")

    if not user.is_active:
        record_audit_event(
            db,
            action="auth.login.disabled",
            organization_id=user.organization_id,
            actor_user_id=user.id,
            actor_email=user.email,
            actor_role=user.role,
            ip_address=ip_address,
        )
        raise AuthError(403, "This user account has been deactivated. Contact your administrator.")

    if needs_rehash:
        user.password_hash = _ph.hash(password)

    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = now

    session_row, raw_refresh = _create_refresh_session(
        db, user, settings, ip_address=ip_address, user_agent=user_agent
    )
    access_token, expires_in = issue_access_jwt(user, session_row.id, settings)

    record_audit_event(
        db,
        action="auth.login.succeeded",
        organization_id=user.organization_id,
        actor_user_id=user.id,
        actor_email=user.email,
        actor_role=user.role,
        target_type="session",
        target_id=session_row.id,
        ip_address=ip_address,
    )

    return {
        "access_token": access_token,
        "refresh_token": raw_refresh,
        "token_type": "bearer",
        "expires_in": expires_in,
        "user": serialize_user(user),
    }


def rotate_refresh_session(
    db: Session,
    settings,
    *,
    raw_refresh_token: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    cleaned = (raw_refresh_token or "").strip()
    if not cleaned:
        raise AuthError(401, "Missing refresh token.")

    token_hash = hash_opaque_token(cleaned)
    session_row = db.scalar(select(UserSession).where(UserSession.token_hash == token_hash))
    if session_row is None:
        raise AuthError(401, "Invalid refresh session.")

    now = utc_now()

    # Reuse detection: if an already-rotated token is replayed, revoke the entire token family!
    if session_row.revoked_at is not None:
        if session_row.replaced_by_id is not None:
            family_rows = db.scalars(
                select(UserSession).where(
                    UserSession.family_id == session_row.family_id,
                    UserSession.revoked_at.is_(None),
                )
            ).all()
            for sibling in family_rows:
                sibling.revoked_at = now
            record_audit_event(
                db,
                action="auth.session.reuse_detected",
                actor_user_id=session_row.user_id,
                target_type="session_family",
                target_id=session_row.family_id,
                ip_address=ip_address,
            )
            db.flush()
        raise AuthError(401, "Refresh session has been revoked. Please sign in again.")

    expires_at = _as_utc(session_row.expires_at)
    if expires_at is None or expires_at <= now:
        session_row.revoked_at = now
        db.flush()
        raise AuthError(401, "Refresh session has expired. Please sign in again.")

    user = db.get(User, session_row.user_id)
    if user is None or not user.is_active:
        session_row.revoked_at = now
        db.flush()
        raise AuthError(403, "User account is inactive.")

    new_session, new_raw_refresh = _create_refresh_session(
        db,
        user,
        settings,
        ip_address=ip_address,
        user_agent=user_agent,
        family_id=session_row.family_id,
    )
    session_row.revoked_at = now
    session_row.replaced_by_id = new_session.id
    db.flush()

    access_token, expires_in = issue_access_jwt(user, new_session.id, settings)
    return {
        "access_token": access_token,
        "refresh_token": new_raw_refresh,
        "token_type": "bearer",
        "expires_in": expires_in,
        "user": serialize_user(user),
    }


def revoke_session_by_refresh_token(db: Session, raw_refresh_token: str | None) -> bool:
    cleaned = (raw_refresh_token or "").strip()
    if not cleaned:
        return False
    token_hash = hash_opaque_token(cleaned)
    session_row = db.scalar(select(UserSession).where(UserSession.token_hash == token_hash))
    if session_row and session_row.revoked_at is None:
        session_row.revoked_at = utc_now()
        db.flush()
        return True
    return False


def revoke_all_user_sessions(db: Session, user_id: str, *, except_session_id: str | None = None) -> int:
    now = utc_now()
    rows = db.scalars(
        select(UserSession).where(
            UserSession.user_id == user_id,
            UserSession.revoked_at.is_(None),
        )
    ).all()
    count = 0
    for row in rows:
        if except_session_id and row.id == except_session_id:
            continue
        row.revoked_at = now
        count += 1
    db.flush()
    return count


def create_user_invite(
    db: Session,
    *,
    organization_id: str,
    email: str,
    full_name: str,
    role: str,
    invited_by_user_id: str | None,
    expires_in_hours: int = 72,
    ip_address: str | None = None,
) -> tuple[UserInvite, str]:
    cleaned_email = normalize_email(email)
    cleaned_role = validate_role(role)
    cleaned_name = (full_name or "").strip()
    if not cleaned_name:
        raise AuthError(422, "Full name is required.")

    existing_user = db.scalar(select(User).where(User.email == cleaned_email))
    if existing_user is not None:
        raise AuthError(409, f"A user with email {cleaned_email} already exists.")

    # Revoke any older unaccepted invites for the same email so only the newest link is active
    now = utc_now()
    prior_invites = db.scalars(
        select(UserInvite).where(
            UserInvite.email == cleaned_email,
            UserInvite.accepted_at.is_(None),
            UserInvite.revoked_at.is_(None),
        )
    ).all()
    for inv in prior_invites:
        inv.revoked_at = now

    raw_token = secrets.token_urlsafe(36)
    invite = UserInvite(
        organization_id=organization_id,
        email=cleaned_email,
        full_name=cleaned_name[:160],
        role=cleaned_role,
        token_hash=hash_opaque_token(raw_token),
        invited_by_user_id=invited_by_user_id,
        expires_at=now + timedelta(hours=max(1, min(expires_in_hours, 336))),
    )
    db.add(invite)
    db.flush()

    record_audit_event(
        db,
        action="auth.invite.created",
        organization_id=organization_id,
        actor_user_id=invited_by_user_id,
        target_type="invite",
        target_id=invite.id,
        metadata={"invited_email": cleaned_email, "assigned_role": cleaned_role},
        ip_address=ip_address,
    )
    return invite, raw_token


def inspect_invite_token(db: Session, raw_token: str) -> dict[str, Any]:
    cleaned = (raw_token or "").strip()
    if not cleaned:
        raise AuthError(400, "Missing invitation token.")
    invite = db.scalar(
        select(UserInvite).where(UserInvite.token_hash == hash_opaque_token(cleaned))
    )
    if invite is None:
        raise AuthError(404, "Invitation link is invalid.")
    if invite.accepted_at is not None:
        raise AuthError(410, "This invitation has already been accepted.")
    if invite.revoked_at is not None:
        raise AuthError(410, "This invitation was revoked by an administrator.")
    expires_at = _as_utc(invite.expires_at)
    if expires_at is None or expires_at <= utc_now():
        raise AuthError(410, "This invitation link has expired.")

    org = db.get(Organization, invite.organization_id)
    return {
        "email": invite.email,
        "full_name": invite.full_name,
        "role": invite.role,
        "organization_name": org.name if org else "Halite Workspace",
        "expires_at": expires_at.isoformat(),
    }


def accept_user_invite(
    db: Session,
    settings,
    *,
    raw_token: str,
    password: str,
    full_name: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    cleaned = (raw_token or "").strip()
    if not cleaned:
        raise AuthError(400, "Missing invitation token.")

    invite = db.scalar(
        select(UserInvite).where(UserInvite.token_hash == hash_opaque_token(cleaned))
    )
    if invite is None:
        raise AuthError(404, "Invitation link is invalid.")
    if invite.accepted_at is not None:
        raise AuthError(410, "This invitation has already been accepted.")
    if invite.revoked_at is not None:
        raise AuthError(410, "This invitation was revoked by an administrator.")

    now = utc_now()
    expires_at = _as_utc(invite.expires_at)
    if expires_at is None or expires_at <= now:
        raise AuthError(410, "This invitation link has expired.")

    existing = db.scalar(select(User).where(User.email == invite.email))
    if existing is not None:
        raise AuthError(409, "An account for this email already exists.")

    final_name = (full_name or invite.full_name or "").strip()
    if not final_name:
        raise AuthError(422, "Full name is required.")

    pw_hash = hash_password(password)
    user = User(
        organization_id=invite.organization_id,
        email=invite.email,
        full_name=final_name[:160],
        password_hash=pw_hash,
        role=invite.role,
        is_active=True,
        last_login_at=now,
    )
    invite.accepted_at = now
    db.add(user)
    db.flush()

    session_row, raw_refresh = _create_refresh_session(
        db, user, settings, ip_address=ip_address, user_agent=user_agent
    )
    access_token, expires_in = issue_access_jwt(user, session_row.id, settings)

    record_audit_event(
        db,
        action="auth.invite.accepted",
        organization_id=user.organization_id,
        actor_user_id=user.id,
        actor_email=user.email,
        actor_role=user.role,
        target_type="invite",
        target_id=invite.id,
        ip_address=ip_address,
    )

    org = db.get(Organization, user.organization_id)
    return {
        "access_token": access_token,
        "refresh_token": raw_refresh,
        "token_type": "bearer",
        "expires_in": expires_in,
        "user": serialize_user(user, org),
    }


def count_active_admins(db: Session, organization_id: str) -> int:
    count = db.scalar(
        select(func.count())
        .select_from(User)
        .where(
            User.organization_id == organization_id,
            User.role == "admin",
            User.is_active.is_(True),
        )
    )
    return int(count or 0)
