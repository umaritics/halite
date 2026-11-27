"""Record integrity route registration point; populated by its vertical owner."""
from fastapi import APIRouter

router = APIRouter(prefix="/integrity", tags=["integrity"])


@router.get("/summary")
def summary():
    return {"title": "Record integrity", "link": "/app/integrity", "stats": []}
