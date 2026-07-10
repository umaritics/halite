from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from agents.decision_agent import DecisionAgent
from api.deps import get_graph_repo, get_groq_service

router = APIRouter(prefix="/decisions", tags=["decisions"])


class DecisionCreate(BaseModel):
    title: str
    reasoning: str
    related_component_names: list[str] = []
    linked_ticket_ids: list[str] = []
    created_by: str = "user"


class DecisionUpdate(BaseModel):
    title: str | None = None
    reasoning: str | None = None
    status: str | None = None


class InvalidateRequest(BaseModel):
    note: str


@router.get("")
def list_decisions(status: str | None = None, graph_repo=Depends(get_graph_repo)):
    return graph_repo.list_decisions(status)


@router.post("")
def create_decision(body: DecisionCreate, graph_repo=Depends(get_graph_repo), groq_service=Depends(get_groq_service)):
    agent = DecisionAgent(graph_repo, groq_service)
    return agent.run(body.model_dump())


@router.get("/{decision_id}")
def get_decision(decision_id: str, graph_repo=Depends(get_graph_repo)):
    decision = graph_repo.get_decision(decision_id)
    if not decision:
        raise HTTPException(404, "Decision not found")
    return decision


@router.patch("/{decision_id}")
def update_decision(decision_id: str, body: DecisionUpdate, graph_repo=Depends(get_graph_repo)):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    decision = graph_repo.update_decision(decision_id, updates)
    if not decision:
        raise HTTPException(404, "Decision not found")
    return decision


@router.delete("/{decision_id}")
def delete_decision(decision_id: str, graph_repo=Depends(get_graph_repo)):
    if not graph_repo.delete_decision(decision_id):
        raise HTTPException(404, "Decision not found")
    return {"deleted": True}


@router.post("/{decision_id}/invalidate")
def invalidate_decision(decision_id: str, body: InvalidateRequest, graph_repo=Depends(get_graph_repo)):
    decision = graph_repo.update_decision(
        decision_id,
        {"status": "invalidated", "invalidation_note": body.note},
    )
    if not decision:
        raise HTTPException(404, "Decision not found")
    return decision
