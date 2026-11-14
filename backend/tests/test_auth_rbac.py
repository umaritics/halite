"""
Integration tests for Halite M01 Workspace Authentication, Invite-Only Onboarding,
Rotating Refresh Sessions (with reuse theft detection), RBAC, and Reviewer Audit Trail.
"""
from __future__ import annotations

import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Settings
from tests.conftest import _build_test_app

STRONG_SECRET = "test-jwt-signing-secret-with-at-least-36-bytes!"
ADMIN_EMAIL = "umar.admin@halite.pk"
ADMIN_PASS = "HaliteAdminPass2026"


def _auth_settings(tmp_path, **overrides) -> Settings:
    db_file = tmp_path / "auth_test.sqlite3"
    base = {
        "DEMO_MODE": False,
        "SECRET_KEY": STRONG_SECRET,
        "HALITE_API_KEY": "server-to-server-api-key-32-characters-long",
        "OPS_TOKEN": "ops-token-privileged-32-characters-long",
        "DATABASE_URL": f"sqlite:///{db_file.as_posix()}",
        "BOOTSTRAP_ADMIN_EMAIL": ADMIN_EMAIL,
        "BOOTSTRAP_ADMIN_PASSWORD": ADMIN_PASS,
        "BOOTSTRAP_ADMIN_NAME": "Muhammad Umar",
        "AUTH_MAX_FAILED_ATTEMPTS": 4,
        "AUTH_LOCKOUT_MINUTES": 15,
        "RATE_LIMIT_AUTH_FAILURES_PER_MINUTE": 50,
    }
    base.update(overrides)
    return Settings(**base)


@pytest.fixture()
def auth_client(tmp_path):
    app = _build_test_app(_auth_settings(tmp_path))
    with TestClient(app) as tc:
        yield tc


def _login(tc: TestClient, email: str, password: str) -> dict:
    resp = tc.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()


def _invite_and_accept(
    tc: TestClient,
    admin_token: str,
    *,
    email: str,
    full_name: str,
    role: str,
    password: str = "ValidMemberPass2026",
) -> dict:
    inv = tc.post(
        "/api/admin/invites",
        json={"email": email, "full_name": full_name, "role": role},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert inv.status_code == 201, inv.text
    raw_token = inv.json()["invite_token"]

    preview = tc.get("/api/auth/invites/verify", params={"token": raw_token})
    assert preview.status_code == 200
    assert preview.json()["email"] == email
    assert preview.json()["role"] == role

    accepted = tc.post(
        "/api/auth/invites/accept",
        json={"token": raw_token, "password": password, "full_name": full_name},
    )
    assert accepted.status_code == 200, accepted.text
    return accepted.json()


class TestAuthenticationAndSessions:
    def test_bootstrap_admin_login_me_and_logout_revokes_access_jwt_immediately(
        self, auth_client: TestClient
    ):
        session = _login(auth_client, ADMIN_EMAIL, ADMIN_PASS)
        access = session["access_token"]
        refresh = session["refresh_token"]
        assert session["user"]["role"] == "admin"
        assert session["user"]["email"] == ADMIN_EMAIL

        me = auth_client.get("/api/auth/me", headers={"Authorization": f"Bearer {access}"})
        assert me.status_code == 200
        assert me.json()["full_name"] == "Muhammad Umar"

        # Logout revokes the underlying UserSession row -> even unexpired JWT is immediately rejected
        out = auth_client.post("/api/auth/logout", json={"refresh_token": refresh})
        assert out.status_code == 200
        after_logout = auth_client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {access}"}
        )
        assert after_logout.status_code == 401

    def test_unknown_email_and_account_lockout_protection(self, auth_client: TestClient):
        unknown = auth_client.post(
            "/api/auth/login",
            json={"email": "nobody@halite.pk", "password": "WrongPassword123"},
        )
        assert unknown.status_code == 401

        # 4 wrong attempts lock the account -> 5th returns 429 even with right password
        for _ in range(4):
            bad = auth_client.post(
                "/api/auth/login",
                json={"email": ADMIN_EMAIL, "password": "WrongPassword123"},
            )
            assert bad.status_code == 401

        locked = auth_client.post(
            "/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASS},
        )
        assert locked.status_code == 429
        assert "locked" in locked.json()["detail"].lower()

    def test_refresh_rotation_and_stolen_token_reuse_revokes_entire_family(
        self, auth_client: TestClient
    ):
        initial = _login(auth_client, ADMIN_EMAIL, ADMIN_PASS)
        r1 = initial["refresh_token"]

        rotated = auth_client.post("/api/auth/refresh", json={"refresh_token": r1})
        assert rotated.status_code == 200
        r2 = rotated.json()["refresh_token"]
        a2 = rotated.json()["access_token"]
        assert r2 != r1

        # Replaying old rotated token r1 triggers family-wide theft revocation!
        replay = auth_client.post("/api/auth/refresh", json={"refresh_token": r1})
        assert replay.status_code == 401

        # Both r2 and a2 from the compromised family are now revoked
        assert auth_client.post("/api/auth/refresh", json={"refresh_token": r2}).status_code == 401
        assert (
            auth_client.get("/api/auth/me", headers={"Authorization": f"Bearer {a2}"}).status_code
            == 401
        )


class TestInviteOnlyAndRbacAuditTrail:
    def test_invite_single_use_and_weak_password_validation(self, auth_client: TestClient):
        admin_token = _login(auth_client, ADMIN_EMAIL, ADMIN_PASS)["access_token"]
        inv = auth_client.post(
            "/api/admin/invites",
            json={"email": "shahmeer@halite.pk", "full_name": "Shahmeer Atif", "role": "technician"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert inv.status_code == 201
        raw_token = inv.json()["invite_token"]

        # Weak password rejected without burning the invite token
        weak = auth_client.post(
            "/api/auth/invites/accept",
            json={"token": raw_token, "password": "short"},
        )
        assert weak.status_code == 422

        no_digits = auth_client.post(
            "/api/auth/invites/accept",
            json={"token": raw_token, "password": "onlyletterslongpassword"},
        )
        assert no_digits.status_code == 422

        # Valid password succeeds
        ok = auth_client.post(
            "/api/auth/invites/accept",
            json={"token": raw_token, "password": "StrongTechPass2026"},
        )
        assert ok.status_code == 200
        assert ok.json()["user"]["role"] == "technician"

        # Second attempt with the same token returns 410 Gone
        reused = auth_client.post(
            "/api/auth/invites/accept",
            json={"token": raw_token, "password": "StrongTechPass2026"},
        )
        assert reused.status_code == 410

    def test_rbac_enforcement_and_reviewer_audit_provenance(self, auth_client: TestClient):
        # Seed two maintenance records in needs_review
        repo = auth_client.app.state.graph_repo
        asset = repo.find_or_create_asset("N813SK", {"make": "Airbus", "model": "A321"})
        for rid in ("RBAC-REC-1", "RBAC-REC-2"):
            repo.create_service_record(
                {
                    "record_id": rid,
                    "asset_key": "N813SK",
                    "occurred_at": "2025-05-01",
                    "part_name": "PUMP",
                    "text": f"Discrepancy on {rid}",
                    "status": "needs_review",
                    "confidence": 0.42,
                }
            )
            repo.link_record_about_asset(rid, asset["id"])

        admin_token = _login(auth_client, ADMIN_EMAIL, ADMIN_PASS)["access_token"]
        tech = _invite_and_accept(
            auth_client,
            admin_token,
            email="tech@halite.pk",
            full_name="Line Technician",
            role="technician",
        )
        sup = _invite_and_accept(
            auth_client,
            admin_token,
            email="usman.sup@halite.pk",
            full_name="Usman Supervisor",
            role="supervisor",
        )

        tech_headers = {"Authorization": f"Bearer {tech['access_token']}"}
        sup_headers = {"Authorization": f"Bearer {sup['access_token']}"}
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # Technician CAN read assets & review queue
        assert auth_client.get("/api/maintenance/assets", headers=tech_headers).status_code == 200
        assert (
            auth_client.get("/api/maintenance/review-queue", headers=tech_headers).status_code == 200
        )

        # Technician CANNOT accept/reject conflict reviews (403) or access /api/admin/* (403)
        assert (
            auth_client.post(
                "/api/maintenance/review-queue/RBAC-REC-1/accept",
                json={"note": "tech attempt"},
                headers=tech_headers,
            ).status_code
            == 403
        )
        assert (
            auth_client.post(
                "/api/maintenance/review-queue/RBAC-REC-1/reject",
                json={"note": "tech reject attempt"},
                headers=tech_headers,
            ).status_code
            == 403
        )
        assert auth_client.get("/api/admin/users", headers=tech_headers).status_code == 403

        # Supervisor CAN accept/reject conflict reviews, but CANNOT access /api/admin/* (403)
        assert auth_client.get("/api/admin/users", headers=sup_headers).status_code == 403

        acc = auth_client.post(
            "/api/maintenance/review-queue/RBAC-REC-1/accept",
            json={"note": "Confirmed pump replacement supersedes prior leak report"},
            headers=sup_headers,
        )
        assert acc.status_code == 200
        rec1 = acc.json()["record"]
        assert rec1["reviewed_by_email"] == "usman.sup@halite.pk"
        assert rec1["reviewed_by_name"] == "Usman Supervisor"
        assert rec1["reviewed_by_role"] == "supervisor"
        assert rec1["reviewed_at"]

        rej = auth_client.post(
            "/api/maintenance/review-queue/RBAC-REC-2/reject",
            json={"note": "Different JASC system, keep both records active"},
            headers=sup_headers,
        )
        assert rej.status_code == 200
        assert rej.json()["record"]["reviewed_by_email"] == "usman.sup@halite.pk"

        # Admin sees immutable review events in /api/admin/audit-events
        audit = auth_client.get("/api/admin/audit-events", headers=admin_headers)
        assert audit.status_code == 200
        actions = [item["action"] for item in audit.json()["items"]]
        assert "maintenance.review.accepted" in actions
        assert "maintenance.review.rejected" in actions

    def test_admin_user_governance_prevents_self_lockout_and_revokes_deactivated_user(
        self, auth_client: TestClient
    ):
        admin_session = _login(auth_client, ADMIN_EMAIL, ADMIN_PASS)
        admin_headers = {"Authorization": f"Bearer {admin_session['access_token']}"}
        admin_id = admin_session["user"]["id"]

        # Admin cannot deactivate or demote themselves
        assert (
            auth_client.patch(
                f"/api/admin/users/{admin_id}",
                json={"is_active": False},
                headers=admin_headers,
            ).status_code
            == 400
        )
        assert (
            auth_client.patch(
                f"/api/admin/users/{admin_id}",
                json={"role": "technician"},
                headers=admin_headers,
            ).status_code
            == 400
        )

        # Deactivating a technician immediately invalidates their live JWT
        tech = _invite_and_accept(
            auth_client,
            admin_session["access_token"],
            email="temp.tech@halite.pk",
            full_name="Temp Tech",
            role="technician",
        )
        tech_id = tech["user"]["id"]
        tech_headers = {"Authorization": f"Bearer {tech['access_token']}"}
        assert auth_client.get("/api/auth/me", headers=tech_headers).status_code == 200

        deact = auth_client.patch(
            f"/api/admin/users/{tech_id}",
            json={"is_active": False},
            headers=admin_headers,
        )
        assert deact.status_code == 200
        assert deact.json()["is_active"] is False

        assert auth_client.get("/api/auth/me", headers=tech_headers).status_code == 401
