from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_graph_repo

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
