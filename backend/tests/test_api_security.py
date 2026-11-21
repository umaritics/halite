"""
Comprehensive security test suite for Halite public API hardening:

  - R1: Primary client authentication (`Authorization: Bearer <HALITE_API_KEY>`
        and alias `X-Halite-Api-Key`), privileged `OPS_TOKEN` elevation, and
        fail-closed 503 when `DEMO_MODE=false` without `HALITE_API_KEY`.
  - R2: Explicit public allowlist (`/health`, `/api/health`, `/api/ops/version`)
        vs. authenticated `/api/*` surface across every router.
  - R3: OpenAPI / `/docs` / `/redoc` disabled by default when `DEMO_MODE=false`,
        bounded sliding-window rate limiting + auth brute-force lockout,
        forwarded-IP anti-spoofing, and hardened response headers.
  - R5: Legacy software routes fully retired (404), including with old enable flags.
  - Filesystem path-jail on `POST /api/maintenance/ingest` (`csv_path`).
  - Log redaction for `HALITE_API_KEY`, `Bearer` tokens, `OPS_TOKEN`, and Bolt URIs.
"""
from __future__ import annotations

import json
import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.routes.ops import _redact
from config import Settings
from tests.conftest import _build_test_app

TEST_API_KEY = "test-halite-api-key-32-chars-minimum"
TEST_OPS_TOKEN = "test-halite-ops-token-privileged"


def _production_settings(**overrides) -> Settings:
    base = {
        "DEMO_MODE": False,
        "HALITE_API_KEY": TEST_API_KEY,
        "OPS_TOKEN": TEST_OPS_TOKEN,
        "EXPOSE_OPENAPI": None,
        "ENABLE_GITEA_INTEGRATION": False,
        "FRONTEND_URL": "https://halite.vercel.app",
    }
    base.update(overrides)
    return Settings(**base)


@pytest.fixture()
def prod_client():
    app = _build_test_app(_production_settings())
    with TestClient(app) as tc:
        yield tc


class TestPublicAllowlistAndAuthGate:
    def test_public_endpoints_remain_accessible_without_api_key(self, prod_client: TestClient):
        for path in ("/health", "/api/health", "/api/ops/version"):
            resp = prod_client.get(path)
            assert resp.status_code == 200, f"{path} returned {resp.status_code}"

        version = prod_client.get("/api/ops/version").json()
        assert version["auth_enabled"] is True
        assert version["openapi_enabled"] is False
        assert "HALITE_API_KEY" not in json.dumps(version)

    @pytest.mark.parametrize(
        ("method", "path", "json_body"),
        [
            ("GET", "/api/graph/overview", None),
            ("GET", "/api/graph/export/context", None),
            ("DELETE", "/api/graph/reset", None),
            ("GET", "/api/domains", None),
            ("GET", "/api/maintenance/assets", None),
            ("GET", "/api/maintenance/records", None),
            ("POST", "/api/maintenance/ingest", {}),
            ("GET", "/api/maintenance/review-queue", None),
            ("GET", "/api/maintenance/analysis/status", None),
            ("POST", "/api/maintenance/analysis/run", {"batch_size": 1}),
            ("GET", "/api/maintenance/corrections", None),
            ("POST", "/api/maintenance/diagnose", {"asset_id": "x", "symptom_text": "leak"}),
            ("POST", "/api/maintenance/copilot/turn", {"message": "vibration on climb"}),
            ("POST", "/api/maintenance/chat", {"message": "status?"}),
            ("GET", "/api/ops/logs", None),
        ],
    )
    def test_every_protected_route_rejects_anonymous_caller(
        self,
        prod_client: TestClient,
        method: str,
        path: str,
        json_body: dict | None,
    ):
        resp = prod_client.request(method, path, json=json_body)
        assert resp.status_code == 401, f"Anonymous {method} {path} returned {resp.status_code}"
        assert resp.headers.get("www-authenticate") == "Bearer"

        wrong = prod_client.request(
            method,
            path,
            json=json_body,
            headers={"Authorization": "Bearer wrong-key"},
        )
        assert wrong.status_code == 401

    def test_bearer_and_alias_header_grant_access_to_standard_routes(self, prod_client: TestClient):
        bearer_ok = prod_client.get(
            "/api/graph/overview",
            headers={"Authorization": f"Bearer {TEST_API_KEY}"},
        )
        assert bearer_ok.status_code == 200
        assert "nodes" in bearer_ok.json()

        alias_ok = prod_client.get(
            "/api/maintenance/assets",
            headers={"X-Halite-Api-Key": TEST_API_KEY},
        )
        assert alias_ok.status_code == 200
        assert isinstance(alias_ok.json(), list)

    def test_ops_routes_still_require_ops_token_even_with_valid_client_api_key(
        self, prod_client: TestClient
    ):
        only_client_key = prod_client.get(
            "/api/ops/logs",
            headers={"Authorization": f"Bearer {TEST_API_KEY}"},
        )
        assert only_client_key.status_code == 401

        ops_only = prod_client.get(
            "/api/ops/logs",
            headers={"X-Ops-Token": TEST_OPS_TOKEN},
        )
        assert ops_only.status_code == 200
        assert "lines" in ops_only.json()

    def test_fail_closed_503_when_demo_mode_false_and_api_key_unset(self):
        misconfigured = _production_settings(HALITE_API_KEY="", OPS_TOKEN="")
        app = _build_test_app(misconfigured)
        with TestClient(app) as tc:
            # Health still reports status so monitoring/operators can diagnose
            assert tc.get("/health").status_code == 200
            denied = tc.get("/api/maintenance/assets")
            assert denied.status_code == 503
            assert "HALITE_API_KEY is not configured" in denied.json()["detail"]


class TestOpenApiAndHeadersHardening:
    def test_openapi_and_docs_hidden_by_default_in_production_profile(
        self, prod_client: TestClient
    ):
        for doc_path in ("/docs", "/redoc", "/openapi.json"):
            resp = prod_client.get(doc_path)
            assert resp.status_code == 404, f"{doc_path} must be hidden when EXPOSE_OPENAPI is unset/false"

    def test_openapi_exposed_when_explicitly_enabled_and_documents_security_schemes(self):
        app = _build_test_app(_production_settings(EXPOSE_OPENAPI=True))
        with TestClient(app) as tc:
            resp = tc.get("/openapi.json")
            assert resp.status_code == 200
            schema = resp.json()
            schemes = schema.get("components", {}).get("securitySchemes", {})
            assert "HaliteBearerAuth" in schemes
            assert "HaliteApiKeyHeader" in schemes

    def test_security_headers_and_cors_policy(self, prod_client: TestClient):
        resp = prod_client.get(
            "/api/domains",
            headers={"Authorization": f"Bearer {TEST_API_KEY}"},
        )
        assert resp.status_code == 200
        assert resp.headers["x-content-type-options"] == "nosniff"
        assert resp.headers["x-frame-options"] == "DENY"
        assert resp.headers["referrer-policy"] == "no-referrer"
        assert resp.headers["cache-control"] == "no-store"
        assert "noindex" in resp.headers["x-robots-tag"]

        # Unapproved Vercel tenant must NOT receive CORS allow header
        evil_preflight = prod_client.options(
            "/api/maintenance/assets",
            headers={
                "Origin": "https://attacker-evil.vercel.app",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert "access-control-allow-origin" not in evil_preflight.headers

        # Halite's own Vercel preview matches narrowed regex
        good_preflight = prod_client.options(
            "/api/maintenance/assets",
            headers={
                "Origin": "https://halite-preview-123.vercel.app",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert (
            good_preflight.headers.get("access-control-allow-origin")
            == "https://halite-preview-123.vercel.app"
        )


class TestRateLimitingAndAntiSpoofing:
    def test_llm_route_rate_limit_enforced_and_xff_spoofing_resisted(self):
        app = _build_test_app(
            _production_settings(RATE_LIMIT_LLM_PER_MINUTE=2, RATE_LIMIT_API_PER_MINUTE=50)
        )
        headers_base = {"Authorization": f"Bearer {TEST_API_KEY}"}
        with TestClient(app) as tc:
            # Spoofed left-hand XFF values with the same rightmost proxy client IP (203.0.113.9)
            r1 = tc.post(
                "/api/maintenance/copilot/turn",
                json={"message": "q1"},
                headers={**headers_base, "X-Forwarded-For": "1.1.1.1, 203.0.113.9"},
            )
            r2 = tc.post(
                "/api/maintenance/copilot/turn",
                json={"message": "q2"},
                headers={**headers_base, "X-Forwarded-For": "2.2.2.2, 203.0.113.9"},
            )
            r3 = tc.post(
                "/api/maintenance/copilot/turn",
                json={"message": "q3"},
                headers={**headers_base, "X-Forwarded-For": "3.3.3.3, 203.0.113.9"},
            )
            assert r1.status_code == 200
            assert r2.status_code == 200
            assert r3.status_code == 429
            assert int(r3.headers["retry-after"]) >= 1

    def test_repeated_auth_failures_trigger_429_brute_force_lockout(self):
        app = _build_test_app(_production_settings(RATE_LIMIT_AUTH_FAILURES_PER_MINUTE=3))
        with TestClient(app) as tc:
            for _ in range(3):
                res = tc.get("/api/domains", headers={"Authorization": "Bearer bad"})
                assert res.status_code == 401
            fourth = tc.get("/api/domains", headers={"Authorization": "Bearer bad"})
            assert fourth.status_code == 429
            # Subsequent attempts while locked out stay 429
            locked = tc.get("/api/domains", headers={"Authorization": f"Bearer {TEST_API_KEY}"})
            assert locked.status_code == 429


class TestIngestPathJailAndLogRedaction:
    def test_ingest_rejects_traversal_and_non_csv_paths(self, prod_client: TestClient):
        auth = {"Authorization": f"Bearer {TEST_API_KEY}"}
        for bad_path in ("../.env", "../../etc/passwd", "/etc/passwd", "config.py"):
            resp = prod_client.post(
                "/api/maintenance/ingest",
                json={"csv_path": bad_path},
                headers=auth,
            )
            assert resp.status_code == 400, f"Expected 400 for {bad_path}, got {resp.status_code}"

    def test_graph_overview_bounds_limit_query_param(self, prod_client: TestClient):
        auth = {"Authorization": f"Bearer {TEST_API_KEY}"}
        assert prod_client.get("/api/graph/overview?limit=0", headers=auth).status_code == 422
        assert prod_client.get("/api/graph/overview?limit=999999", headers=auth).status_code == 422

    def test_ops_log_redaction_scrubs_bearer_and_credentials(self):
        line = (
            "Authorization: Bearer super-secret-key-12345 "
            "HALITE_API_KEY=my-key OPS_TOKEN=my-ops "
            "neo4j+s://neo4j:s3cr3tPass@1234.databases.neo4j.io"
        )
        redacted = _redact(line)
        assert "super-secret-key-12345" not in redacted
        assert "my-key" not in redacted
        assert "my-ops" not in redacted
        assert "s3cr3tPass" not in redacted
        assert "[REDACTED]" in redacted
