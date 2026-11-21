"""Model registry: preserve identity imports and discover vertical tables."""
from .identity import (
    AuditEvent, Base, Organization, User, UserInvite, UserSession, VALID_ROLES, utc_now,
)
from . import evaluation, integrity, sessions

__all__ = [
    "AuditEvent", "Base", "Organization", "User", "UserInvite", "UserSession",
    "VALID_ROLES", "utc_now", "evaluation", "integrity", "sessions",
]
