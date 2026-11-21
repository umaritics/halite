"""Retired surfaces cannot reactivate; real startup never injects software data."""
import asyncio

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from config import Settings
from tests.conftest import _build_test_app


@pytest.mark.parametrize('old_enable_flag', [False, True])
def test_retired_routes_are_absent_for_anonymous_and_authenticated_clients(old_enable_flag):
    app = _build_test_app(Settings(
        _env_file=None, DEMO_MODE=False, EXPOSE_OPENAPI=True,
        HALITE_API_KEY='synthetic-retirement-key', ENABLE_GITEA_INTEGRATION=old_enable_flag,
        GITEA_WEBHOOK_SECRET='synthetic-retired-secret',
    ))
    retired = [
        ('POST', '/api/chat'), ('GET', '/api/decisions'),
        ('POST', '/api/decisions'), ('GET', '/api/decisions/example'),
        ('POST', '/api/ingest/document'), ('POST', '/api/ingest/code'),
        ('POST', '/api/ingest/gitea'), ('GET', '/api/alerts'),
        ('POST', '/api/webhook/gitea'),
    ]
    with TestClient(app) as client:
        before_nodes = dict(app.state.graph_repo.store.nodes)
        before_edges = list(app.state.graph_repo.store.edges)
        for headers in ({}, {'Authorization': 'Bearer synthetic-retirement-key'}):
            for method, path in retired:
                response = client.request(method, path, json={}, headers=headers)
                assert response.status_code == 404, (method, path, response.text)
        schema_paths = client.get('/openapi.json').json()['paths']
        assert not any(path.startswith(('/api/chat', '/api/decisions', '/api/ingest',
                                       '/api/alerts', '/api/webhook')) for path in schema_paths)
        assert app.state.graph_repo.store.nodes == before_nodes
        assert app.state.graph_repo.store.edges == before_edges
        assert app.state.groq_service.fallback_invocations == 0


@pytest.mark.parametrize('profile', ['demo', 'neo4j', 'neo4j-unavailable'])
def test_actual_lifespan_preserves_existing_data_and_never_seeds_software(profile, monkeypatch):
    # Import only here: this exercises the real production lifecycle on hosted CI,
    # rather than the deliberately seeded lightweight test-app fixture.
    import main
    from graph.memory_store import MemoryGraphStore
    from graph.queries import GraphRepository

    def forbidden_seed(*args, **kwargs):
        pytest.fail('Production startup must never seed software/demo records')

    monkeypatch.setattr(MemoryGraphStore, 'seed_demo_data', forbidden_seed)
    monkeypatch.setattr(GraphRepository, 'seed_demo_data', forbidden_seed)
    memory_instances = []
    neo_instances = []

    class TrackedMemory(MemoryGraphStore):
        def __init__(self):
            super().__init__()
            self.closed = False
            memory_instances.append(self)

        def close(self):
            self.closed = True

    class FakeNeo4j:
        def __init__(self, *args, **kwargs):
            self.closed = False
            self.schema_called = False
            self.existing_records = {'preexisting-record': 'preserve this data'}
            neo_instances.append(self)

        def init_schema(self):
            self.schema_called = True
            if profile == 'neo4j-unavailable':
                raise RuntimeError('synthetic connectivity failure')

        def close(self):
            self.closed = True

    monkeypatch.setattr(main, 'MemoryGraphStore', TrackedMemory)
    monkeypatch.setattr(main, 'Neo4jClient', FakeNeo4j)
    monkeypatch.setattr(main, 'settings', Settings(
        _env_file=None, DEMO_MODE=profile == 'demo', HALITE_API_KEY='synthetic-key',
        NEO4J_URI='bolt://synthetic.invalid:7687', NEO4J_PASSWORD='synthetic-password',
        DATABASE_URL='sqlite+pysqlite:///:memory:', BOOTSTRAP_ADMIN_EMAIL='',
        GROQ_API_KEY='', OPENAI_COMPAT_API_KEY='', LLM_PROVIDER='groq',
    ))
    app = FastAPI()

    async def exercise():
        async with main.lifespan(app):
            assert app.state.rel_store.ping()
            assert app.state.groq_service.is_live is False
            if profile == 'neo4j':
                assert app.state.graph_repo.is_memory is False
                assert app.state.graph_repo.store is neo_instances[0]
                assert not memory_instances
            else:
                assert app.state.graph_repo.is_memory is True
                assert app.state.graph_repo.store.nodes == {}
                assert app.state.graph_repo.store.edges == []
            for store in neo_instances:
                assert store.schema_called
                assert store.existing_records == {'preexisting-record': 'preserve this data'}

    asyncio.run(exercise())
    assert all(store.closed for store in memory_instances + neo_instances)
    assert len(neo_instances) == (0 if profile == 'demo' else 1)
