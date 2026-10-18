from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse

from api.deps import get_graph_repo
from api.routes.ops import _require_ops_token

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/overview")
def graph_overview(limit: int = 200, graph_repo=Depends(get_graph_repo)):
    return graph_repo.graph_overview(limit)


@router.get("/component/{component_id}")
def component_neighborhood(component_id: str, graph_repo=Depends(get_graph_repo)):
    data = graph_repo.get_neighborhood(component_id)
    if not data:
        raise HTTPException(404, "Component not found")
    return data


@router.get("/decision/{decision_id}")
def decision_neighborhood(decision_id: str, graph_repo=Depends(get_graph_repo)):
    data = graph_repo.get_neighborhood(decision_id)
    if not data:
        raise HTTPException(404, "Decision not found")
    return data


@router.get("/export/context", response_class=PlainTextResponse)
def export_agent_context(graph_repo=Depends(get_graph_repo)):
    return graph_repo.export_agent_context()


@router.delete("/reset", dependencies=[Depends(_require_ops_token)])
def reset_graph(
    seed_demo_data: bool = Query(False),
    confirm: str = Query("", description="Must be WIPE to delete a real Neo4j database"),
    graph_repo=Depends(get_graph_repo),
):
    """
    Wipe all nodes and edges. DESTRUCTIVE: requires the operations token (``X-Ops-Token``).

    The route is unavailable (503) unless ``OPS_TOKEN`` is configured on the server. Wiping a real
    Neo4j database additionally needs ``confirm=WIPE``; the in-memory graph used by tests does not.
    """
    if graph_repo.is_memory:
        graph_repo.store.nodes.clear()
        graph_repo.store.edges.clear()
        if seed_demo_data:
            graph_repo.store.seed_demo_data()
        return {"reset": True, "mode": "memory", "seeded": seed_demo_data}

    if confirm != "WIPE":
        raise HTTPException(400, "Wiping a Neo4j database requires confirm=WIPE")
    graph_repo.store.run_query("MATCH (n) DETACH DELETE n")
    if seed_demo_data:
        graph_repo.seed_demo_data()
    return {"reset": True, "mode": "neo4j", "seeded": seed_demo_data}
