from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_graph_repo

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("")
def list_alerts(graph_repo=Depends(get_graph_repo)):
    return graph_repo.get_alerts()


@router.post("/{decision_id}/acknowledge")
def acknowledge_alert(decision_id: str, graph_repo=Depends(get_graph_repo)):
    decision = graph_repo.update_decision(decision_id, {"status": "active"})
    if not decision:
        raise HTTPException(404, "Decision not found")
    return decision
