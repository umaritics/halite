"""Retrieval and ranking route registration point."""
from fastapi import APIRouter, Depends

from api.deps import get_settings
from retrieval.service import corpus_available, normalize_mode, ranker_version

router = APIRouter(prefix="/retrieval", tags=["retrieval"])


@router.get("/summary")
def summary(settings=Depends(get_settings)):
    mode = normalize_mode(settings.RETRIEVAL_MODE)
    return {
        "title": "Retrieval and ranking",
        "link": "/app/search",
        "mode": mode,
        "ranker_version": ranker_version(mode),
        "corpus_loaded": corpus_available(),
        "stats": [],
    }