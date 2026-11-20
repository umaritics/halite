"""Investigation sessions route registration point; populated by its vertical owner."""
from fastapi import APIRouter

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("/summary")
def summary():
    return {"title": "Investigation sessions", "link": "/app/investigations", "stats": []}
