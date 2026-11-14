"""
conftest.py — shared fixtures for the Halite test suite.

All fixtures use MemoryGraphStore so tests run without Neo4j or Groq.

Design note: we do NOT import main.py in the test fixtures.  The neo4j
packstream module pre-allocates 65 536 dict entries at import time, which
causes MemoryError on some machines.  Instead we build a minimal FastAPI
app with only the routes we need — identical to what main.py would do in
demo mode, but without pulling in the neo4j import chain.
"""
import io
import sys
import os
import pytest
from fastapi.testclient import TestClient

# Ensure 'backend/' is on the import path when pytest is invoked from backend/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ---------------------------------------------------------------------------
# Lightweight stub GroqService — no network calls, deterministic output
# ---------------------------------------------------------------------------

class StubGroqService:
    """Deterministic stub that returns realistic-looking JSON for tests."""
    demo_mode = True
    fallback_invocations = 0

    @property
    def is_live(self) -> bool:
        return False

    def chat(self, messages: list, system_prompt: str | None = None, **_) -> str:
        import json
        self.fallback_invocations += 1
        return json.dumps({
            "decisions": [
                {
                    "title": "Use event-driven architecture",
                    "reasoning": "Decouples services.",
                    "related_components": ["ApiGateway"],
                }
            ]
        })

    def extract_json(self, prompt: str, system_prompt: str | None = None, **_) -> str:
        return self.chat([{"role": "user", "content": prompt}], system_prompt)


# ---------------------------------------------------------------------------
# Graph fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def memory_store():
    """Fresh MemoryGraphStore, no seed data."""
    from graph.memory_store import MemoryGraphStore
    return MemoryGraphStore()


@pytest.fixture()
def seeded_store():
    """MemoryGraphStore with demo data seeded."""
    from graph.memory_store import MemoryGraphStore
    store = MemoryGraphStore()
    store.seed_demo_data()
    return store


@pytest.fixture()
def graph_repo(seeded_store):
    """GraphRepository backed by seeded MemoryGraphStore."""
    from graph.queries import GraphRepository
    return GraphRepository(seeded_store)


@pytest.fixture()
def graph_repo_empty(memory_store):
    """GraphRepository backed by empty MemoryGraphStore."""
    from graph.queries import GraphRepository
    return GraphRepository(memory_store)


@pytest.fixture()
def stub_groq():
    """Stub GroqService with no network calls."""
    return StubGroqService()


# ---------------------------------------------------------------------------
# _build_test_app() — builds a minimal FastAPI app for testing
#
# This function MUST NOT import main.py or Neo4jClient.  We register exactly
# the same routes that main.py registers, but using local imports that do not
# pull in the neo4j packstream init chain.
# ---------------------------------------------------------------------------

def _build_test_app(settings_override=None):
    """
    Build and return a FastAPI app wired for testing.

    Registers all routes via `api.router.register_api_routers`, sets
    app.state.graph_repo / groq_service / settings, and mirrors `main.py`'s
    OpenAPI gating, CORS, and security headers without importing `Neo4jClient`.
    """
    from fastapi import Depends, FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    import config as cfg_module
    settings = settings_override or cfg_module.Settings()

    from api.router import register_api_routers
    from api.security import SecurityHeadersMiddleware, require_public_rate_limit
    from db.session import build_relational_store
    from graph.memory_store import MemoryGraphStore
    from graph.queries import GraphRepository
    from services.auth_service import bootstrap_admin_if_configured
    from services.groq_service import GroqService

    store = MemoryGraphStore()
    store.seed_demo_data()
    graph_repo = GraphRepository(store)
    groq_service = GroqService("", demo_mode=True)
    rel_store = build_relational_store(settings)
    bootstrap_admin_if_configured(rel_store, settings)

    openapi_on = settings.openapi_enabled
    app = FastAPI(
        title="Halite Test App",
        docs_url="/docs" if openapi_on else None,
        redoc_url="/redoc" if openapi_on else None,
        openapi_url="/openapi.json" if openapi_on else None,
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_origin_regex=(settings.CORS_ORIGIN_REGEX or None),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Halite-Api-Key", "X-Ops-Token"],
    )

    register_api_routers(app)

    # Health endpoints (simplified, matching main.py's _health_payload logic)
    from domains.registry import list_domains

    @app.get("/health", dependencies=[Depends(require_public_rate_limit)])
    def health():
        active_settings = app.state.settings
        active_rel = getattr(app.state, "rel_store", None)
        is_memory = graph_repo.is_memory
        maint_count = graph_repo.count_service_records()
        return {
            "status": "ok",
            "app": "Halite",
            "demo_mode": True,
            "neo4j_configured": False,
            "using_memory_graph": is_memory,
            "groq_configured": False,
            "graph_mode": "memory",
            "llm_mode": "fallback",
            "domains": list_domains(),
            "maintenance_corpus_loaded": maint_count > 0,
            "maintenance_record_count": maint_count,
            "fallback_invocations": groq_service.fallback_invocations,
            "auth_enabled": active_settings.api_auth_required,
            "auth_db_mode": active_rel.mode if active_rel else "unconfigured",
            "openapi_enabled": active_settings.openapi_enabled,
        }

    @app.get("/api/health", dependencies=[Depends(require_public_rate_limit)])
    def api_health():
        return health()

    # Wire state
    app.state.graph_repo = graph_repo
    app.state.groq_service = groq_service
    app.state.rel_store = rel_store
    app.state.settings = settings

    return app


# ---------------------------------------------------------------------------
# FastAPI TestClient fixture (demo mode — MemoryGraphStore, StubGroq)
# ---------------------------------------------------------------------------

@pytest.fixture()
def client():
    """
    Full FastAPI test client in demo mode.

    Uses MemoryGraphStore and StubGroqService; no external I/O.
    Does NOT import main.py — uses _build_test_app() instead.
    """
    app = _build_test_app()
    with TestClient(app, raise_server_exceptions=True) as tc:
        yield tc
