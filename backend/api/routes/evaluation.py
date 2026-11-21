"""Retrieval evaluation route registration point; populated by its vertical owner."""
from fastapi import APIRouter

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


@router.get("/summary")
def summary():
    return {"title": "Retrieval evaluation", "link": "/app/evaluation", "stats": []}
