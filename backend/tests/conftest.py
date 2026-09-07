"""
conftest.py — shared fixtures for the Halite test suite.

All fixtures use MemoryGraphStore so tests run without Neo4j or Groq.
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
# FastAPI TestClient fixture (demo mode — MemoryGraphStore, StubGroq)
# ---------------------------------------------------------------------------

@pytest.fixture()
def client(monkeypatch):
    """
    Full FastAPI test client in demo mode.

    Monkeypatches settings so DEMO_MODE=True and GROQ_API_KEY=''.
    Uses MemoryGraphStore and StubGroqService; no external I/O.
    """
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.setenv("NEO4J_URI", "")
    monkeypatch.setenv("NEO4J_PASSWORD", "")

    # Re-import config with patched env
    import importlib
    import config as cfg_module
    importlib.reload(cfg_module)
    settings = cfg_module.Settings()

    from graph.memory_store import MemoryGraphStore
    from graph.queries import GraphRepository
    from services.groq_service import GroqService
    import main as main_module

    # Build app components directly (bypass lifespan for test speed)
    store = MemoryGraphStore()
    store.seed_demo_data()
    gr = GraphRepository(store)
    gs = GroqService("", demo_mode=True)

    app = main_module.app
    app.state.graph_repo = gr
    app.state.groq_service = gs
    app.state.settings = settings

    with TestClient(app, raise_server_exceptions=True) as tc:
        yield tc
