import logging
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.router import register_api_routers
from api.routes.ops import install_ring_buffer_logging
from api.security import SecurityHeadersMiddleware, require_public_rate_limit
from config import settings
from db.session import build_relational_store
from graph.memory_store import MemoryGraphStore
from graph.neo4j_client import Neo4jClient
from graph.queries import GraphRepository
from services.auth_service import bootstrap_admin_if_configured
from services.groq_service import GroqService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    install_ring_buffer_logging()
    if not settings.DEMO_MODE and not settings.api_key_configured:
        logger.error(
            "SECURITY WARNING: DEMO_MODE=false without HALITE_API_KEY; "
            "protected /api/* routes will fail closed with HTTP 503."
        )
    use_demo = settings.DEMO_MODE or not settings.neo4j_configured
    store = None

    if use_demo:
        logger.info("Halite running in DEMO mode (in-memory graph)")
        store = MemoryGraphStore()
        graph_repo = GraphRepository(store)
    else:
        logger.info("Halite connecting to Neo4j AuraDB")
        try:
            store = Neo4jClient(
                settings.NEO4J_URI,
                settings.NEO4J_USERNAME,
                settings.NEO4J_PASSWORD,
                database=settings.NEO4J_DATABASE,
            )
            store.init_schema()
            graph_repo = GraphRepository(store)
            logger.info("Neo4j connected; existing data preserved")
        except Exception as exc:
            logger.error("Neo4j unavailable (%s) — falling back to in-memory graph", exc)
            if store:
                try:
                    store.close()
                except Exception:
                    pass
            store = MemoryGraphStore()
            graph_repo = GraphRepository(store)

    llm_api_key = settings.GROQ_API_KEY
    if settings.LLM_PROVIDER.strip().lower() == "openai_compatible":
        llm_api_key = settings.OPENAI_COMPAT_API_KEY
    groq_service = GroqService(
        llm_api_key,
        settings.llm_model,
        demo_mode=not settings.llm_configured,
        provider=settings.LLM_PROVIDER,
        openai_compat_base_url=settings.OPENAI_COMPAT_BASE_URL,
        request_timeout_s=settings.LLM_REQUEST_TIMEOUT_S,
    )
    logger.info(
        "LLM provider=%s configured=%s model=%s",
        settings.LLM_PROVIDER,
        settings.llm_configured,
        settings.llm_model,
    )

    rel_store = build_relational_store(settings)
    logger.info("Relational auth store mode: %s", rel_store.mode)
    try:
        bootstrap_admin_if_configured(rel_store, settings)
    except Exception as exc:
        logger.error("Admin bootstrap skipped/failed: %s", exc)

    app.state.graph_repo = graph_repo
    app.state.groq_service = groq_service
    app.state.rel_store = rel_store
    app.state.settings = settings

    yield

    rel_store.close()
    store.close()


_openapi_on = settings.openapi_enabled

app = FastAPI(
    title="Halite API",
    description="Maintenance knowledge graph for evidence-backed diagnostics",
    lifespan=lifespan,
    docs_url="/docs" if _openapi_on else None,
    redoc_url="/redoc" if _openapi_on else None,
    openapi_url="/openapi.json" if _openapi_on else None,
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


def _health_payload():
    active_settings = getattr(app.state, "settings", settings)
    use_memory = active_settings.DEMO_MODE or not active_settings.neo4j_configured
    graph_repo = getattr(app.state, "graph_repo", None)
    is_memory = hasattr(graph_repo, "is_memory") and graph_repo.is_memory

    groq_service = getattr(app.state, "groq_service", None)
    llm_is_live = groq_service.is_live if groq_service else False

    # Maintenance corpus check (always truthful live count; rate limiter caps anonymous floods)
    maintenance_record_count = 0
    maintenance_corpus_loaded = False
    if graph_repo:
        try:
            maintenance_record_count = graph_repo.count_service_records()
            maintenance_corpus_loaded = maintenance_record_count > 0
        except Exception:
            pass

    from domains.registry import list_domains

    domains = list_domains()

    rel_store = getattr(app.state, "rel_store", None)
    auth_db_mode = rel_store.mode if rel_store is not None else "unconfigured"

    return {
        "status": "ok",
        "app": "Halite",
        "demo_mode": use_memory or is_memory,
        "neo4j_configured": active_settings.neo4j_configured,
        "using_memory_graph": is_memory,
        "groq_configured": active_settings.groq_configured,
        "llm_provider": active_settings.LLM_PROVIDER,
        # §T6 additions
        "graph_mode": "memory" if is_memory else "neo4j",
        "llm_mode": "live" if llm_is_live else "fallback",
        "model": groq_service.model if groq_service else "unknown",
        "maint_threshold": active_settings.MAINT_CONFIDENCE_THRESHOLD,
        "domains": domains,
        "maintenance_corpus_loaded": maintenance_corpus_loaded,
        "maintenance_record_count": maintenance_record_count,
        "fallback_invocations": groq_service.fallback_invocations if groq_service else 0,
        "auth_enabled": active_settings.api_auth_required,
        "auth_db_mode": auth_db_mode,
        "openapi_enabled": active_settings.openapi_enabled,
        "git_sha": os.environ.get("GIT_SHA") or active_settings.GIT_SHA or "unknown",
        "deployed_at": os.environ.get("DEPLOYED_AT") or active_settings.DEPLOYED_AT or "",
    }


@app.get("/health", dependencies=[Depends(require_public_rate_limit)])
def health():
    return _health_payload()


@app.get("/api/health", dependencies=[Depends(require_public_rate_limit)])
def api_health():
    return _health_payload()
