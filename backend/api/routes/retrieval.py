"""Retrieval and ranking route registration point; populated by its vertical owner."""
from fastapi import APIRouter

router = APIRouter(prefix="/retrieval", tags=["retrieval"])


@router.get("/summary")
def summary():
    return {"title": "Retrieval and ranking", "link": "/app/search", "stats": []}
