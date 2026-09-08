import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import alerts, chat, decisions, graph, ingest, webhooks
from api.routes.maintenance import domains_router, router as maintenance_router
from api.routes.diagnostics import router as diagnostics_router
from config import settings
from graph.memory_store import MemoryGraphStore
from graph.neo4j_client import Neo4jClient
from graph.queries import GraphRepository
from services.groq_service import GroqService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    use_demo = settings.DEMO_MODE or not settings.neo4j_configured
    store = None

    if use_demo:
        logger.info("Halite running in DEMO mode (in-memory graph)")
        store = MemoryGraphStore()
        store.seed_demo_data()
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
            graph_repo.seed_demo_data()
            logger.info("Neo4j connected and seeded")
        except Exception as exc:
            logger.error("Neo4j unavailable (%s) — falling back to in-memory graph", exc)
            if store:
                try:
                    store.close()
                except Exception:
                    pass
            store = MemoryGraphStore()
            store.seed_demo_data()
            graph_repo = GraphRepository(store)

    groq_service = GroqService(
        settings.GROQ_API_KEY,
        settings.GROQ_MODEL,
        demo_mode=not settings.groq_configured,
    )
    logger.info("Groq configured: %s", settings.groq_configured)

    app.state.graph_repo = graph_repo
    app.state.groq_service = groq_service
    app.state.settings = settings

    yield

    store.close()


app = FastAPI(title="Halite API", description="Living knowledge graph for software project reasoning", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api")
app.include_router(decisions.router, prefix="/api")
app.include_router(graph.router, prefix="/api")
app.include_router(ingest.router, prefix="/api")
app.include_router(webhooks.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")
app.include_router(maintenance_router, prefix="/api")
app.include_router(diagnostics_router, prefix="/api")
app.include_router(domains_router, prefix="/api")


def _health_payload():
    use_memory = settings.DEMO_MODE or not settings.neo4j_configured
    graph_repo = getattr(app.state, "graph_repo", None)
    is_memory = hasattr(graph_repo, "is_memory") and graph_repo.is_memory

    groq_service = getattr(app.state, "groq_service", None)
    llm_is_live = groq_service.is_live if groq_service else False

    # Maintenance corpus check
    maintenance_record_count = 0
    maintenance_corpus_loaded = False
    if graph_repo:
        try:
            records = graph_repo.list_service_records()
            maintenance_record_count = len(records)
            maintenance_corpus_loaded = maintenance_record_count > 0
        except Exception:
            pass

    # Domain list
    from domains.registry import list_domains
    domains = list_domains()

    return {
        "status": "ok",
        "app": "Halite",
        "demo_mode": use_memory or is_memory,
        "neo4j_configured": settings.neo4j_configured,
        "using_memory_graph": is_memory,
        "groq_configured": settings.groq_configured,
        # §T6 additions
        "graph_mode": "memory" if is_memory else "neo4j",
        "llm_mode": "live" if llm_is_live else "fallback",
        "model": groq_service.model if groq_service else "unknown",
        "maint_threshold": settings.MAINT_CONFIDENCE_THRESHOLD,
        "domains": domains,
        "maintenance_corpus_loaded": maintenance_corpus_loaded,
        "maintenance_record_count": maintenance_record_count,
        "fallback_invocations": groq_service.fallback_invocations if groq_service else 0,
    }


@app.get("/health")
def health():
    return _health_payload()


@app.get("/api/health")
def api_health():
    return _health_payload()
