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

def _build_test_app():
    """
    Build and return a FastAPI app wired for testing.

    Registers all routes, sets app.state.graph_repo / groq_service / settings.
    Does not use the lifespan — state is set directly.
    """
    import importlib
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    # Reload config so any env overrides apply
    import config as cfg_module
    settings = cfg_module.Settings()

    from graph.memory_store import MemoryGraphStore
    from graph.queries import GraphRepository
    from services.groq_service import GroqService

    store = MemoryGraphStore()
    store.seed_demo_data()
    graph_repo = GraphRepository(store)
    groq_service = GroqService("", demo_mode=True)

    app = FastAPI(title="Halite Test App")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Software domain routes
    from api.routes import alerts, chat, decisions, graph, ingest, webhooks
    app.include_router(chat.router, prefix="/api")
    app.include_router(decisions.router, prefix="/api")
    app.include_router(graph.router, prefix="/api")
    app.include_router(ingest.router, prefix="/api")
    app.include_router(webhooks.router, prefix="/api")
    app.include_router(alerts.router, prefix="/api")

    # Maintenance domain routes
    from api.routes.maintenance import domains_router, router as maintenance_router
    app.include_router(maintenance_router, prefix="/api")
    app.include_router(domains_router, prefix="/api")

    # Health endpoints (simplified, matching main.py's _health_payload logic)
    from domains.registry import list_domains

    @app.get("/health")
    def health():
        is_memory = graph_repo.is_memory
        llm_is_live = groq_service.is_live
        records = graph_repo.list_service_records()
        maint_count = len(records)
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
        }

    @app.get("/api/health")
    def api_health():
        return health()

    # Wire state
    app.state.graph_repo = graph_repo
    app.state.groq_service = groq_service
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
