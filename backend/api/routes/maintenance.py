"""
api/routes/maintenance.py — REST API for the maintenance domain.

Prefix: /maintenance (registered in main.py as /api prefix)

Endpoints:
  POST  /api/maintenance/ingest           — ingest CSV or inline records
  POST  /api/maintenance/records          — process single record through conflict engine
  GET   /api/maintenance/assets           — list assets with record counts
  GET   /api/maintenance/assets/{id}/history — chronological history
  GET   /api/maintenance/review-queue     — needs_review records, newest first
  POST  /api/maintenance/review-queue/{id}/accept
  POST  /api/maintenance/review-queue/{id}/reject
  GET   /api/domains                      — registered domains for frontend switcher
"""
import logging
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from agents.maintenance_agent import MaintenanceAgent
from api.deps import get_graph_repo, get_groq_service, get_settings
from domains.registry import list_domains
from services.conflict_engine import MAINT_CONFIDENCE_THRESHOLD, process_record

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/maintenance", tags=["maintenance"])
domains_router = APIRouter(tags=["domains"])


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class IngestRequest(BaseModel):
    csv_path: str | None = None
    limit: int | None = None


class RecordProcessRequest(BaseModel):
    record_id: str
    threshold: float | None = None


class ReviewActionRequest(BaseModel):
    note: str | None = None


class RejectActionRequest(BaseModel):
    note: str  # required for rejection


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_maintenance_adapter():
    from domains.registry import get_adapter
    return get_adapter("maintenance")


# ---------------------------------------------------------------------------
# POST /api/maintenance/ingest
# ---------------------------------------------------------------------------

@router.post("/ingest")
def maintenance_ingest(
    body: IngestRequest | None = None,
    graph_repo=Depends(get_graph_repo),
    settings=Depends(get_settings),
):
    """
    Ingest FAA SDR records from a CSV file path.

    Body (JSON): {"csv_path": str, "limit": int | None}

    Returns real counts from the ingestion run.
    """
    if body is None:
        body = IngestRequest()

    # Default csv_path to the processed corpus if not specified
    csv_path = body.csv_path
    if not csv_path:
        csv_path = str(Path(settings.MAINT_DATA_DIR) / "processed" / "sdr_poc_corpus.csv")

    if not Path(csv_path).exists():
        raise HTTPException(
            status_code=404,
            detail=f"CSV file not found: {csv_path}. Run scripts/fetch_sdr_data.py first.",
        )

    payload = {"csv_path": csv_path}
    if body.limit is not None:
        payload["limit"] = body.limit

    agent = MaintenanceAgent(graph_repo, None)
    result = agent.run(payload)
    logger.info("Maintenance ingest: %s", result)
    return result


# ---------------------------------------------------------------------------
# POST /api/maintenance/ingest (multipart upload)
# ---------------------------------------------------------------------------

@router.post("/ingest/upload")
async def maintenance_ingest_upload(
    file: UploadFile = File(...),
    graph_repo=Depends(get_graph_repo),
    settings=Depends(get_settings),
):
    """Upload a CSV file and ingest it directly."""
    import tempfile
    content = await file.read()
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(413, f"File exceeds {settings.MAX_UPLOAD_MB}MB")

    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        agent = MaintenanceAgent(graph_repo, None)
        result = agent.run({"csv_path": tmp_path})
    finally:
        os.unlink(tmp_path)

    return result


# ---------------------------------------------------------------------------
# POST /api/maintenance/records — single record through conflict engine
# ---------------------------------------------------------------------------

@router.post("/records")
def process_single_record(
    body: RecordProcessRequest,
    graph_repo=Depends(get_graph_repo),
    groq_service=Depends(get_groq_service),
    settings=Depends(get_settings),
):
    """
    Run conflict detection on an already-ingested record.

    Body: {"record_id": str, "threshold": float | None}
    """
    adapter = _get_maintenance_adapter()
    threshold = body.threshold if body.threshold is not None else settings.MAINT_CONFIDENCE_THRESHOLD

    # In demo mode (groq not live), run with allow_stub=True so the API still responds
    allow_stub = not groq_service.is_live

    try:
        result = process_record(
            graph_repo, groq_service, adapter, body.record_id,
            threshold=threshold, allow_stub=allow_stub,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return result


# ---------------------------------------------------------------------------
# GET /api/maintenance/assets
# ---------------------------------------------------------------------------

@router.get("/assets")
def list_assets(graph_repo=Depends(get_graph_repo)):
    """List all assets with their record counts."""
    if graph_repo.is_memory:
        assets = graph_repo.store._find_nodes("Asset")
    else:
        rows = graph_repo.store.run_query(
            "MATCH (a:Asset) RETURN a ORDER BY a.tail_number"
        )
        assets = [dict(r["a"]) for r in rows]

    result = []
    for asset in assets:
        count = len(graph_repo.list_asset_history(asset["id"], limit=9999))
        result.append({**asset, "record_count": count})

    result.sort(key=lambda a: a.get("tail_number", ""))
    return result


# ---------------------------------------------------------------------------
# GET /api/maintenance/assets/{asset_id}/history
# ---------------------------------------------------------------------------

@router.get("/assets/{asset_id}/history")
def asset_history(asset_id: str, graph_repo=Depends(get_graph_repo)):
    """Chronological history for a specific asset (ascending by occurred_at)."""
    history = graph_repo.list_asset_history(asset_id, limit=200)
    if not history:
        # Try to find the asset to give a better error
        if graph_repo.is_memory:
            asset = graph_repo.store._get_node(asset_id)
        else:
            rows = graph_repo.store.run_query(
                "MATCH (a:Asset {id: $id}) RETURN a", {"id": asset_id}
            )
            asset = dict(rows[0]["a"]) if rows else None

        if asset is None:
            raise HTTPException(status_code=404, detail=f"Asset {asset_id!r} not found")

    return {"asset_id": asset_id, "records": history, "count": len(history)}


# ---------------------------------------------------------------------------
# GET /api/maintenance/review-queue
# ---------------------------------------------------------------------------

@router.get("/review-queue")
def review_queue(graph_repo=Depends(get_graph_repo)):
    """Records requiring human review (status=needs_review), newest first."""
    records = graph_repo.list_service_records(status="needs_review")
    # Newest first by occurred_at
    records.sort(key=lambda r: r.get("occurred_at", ""), reverse=True)
    return records


# ---------------------------------------------------------------------------
# POST /api/maintenance/review-queue/{record_id}/accept
# ---------------------------------------------------------------------------

@router.post("/review-queue/{record_id}/accept")
def accept_record(
    record_id: str,
    body: ReviewActionRequest | None = None,
    graph_repo=Depends(get_graph_repo),
):
    """Accept a queued record (status → accepted)."""
    note = (body.note if body else None) or ""
    sr = graph_repo.get_service_record(record_id)
    if sr is None:
        raise HTTPException(status_code=404, detail=f"Record {record_id!r} not found")
    if sr.get("status") not in ("needs_review", "auto_accepted"):
        raise HTTPException(
            status_code=409,
            detail=f"Record {record_id!r} is in status '{sr.get('status')}', cannot accept",
        )
    updated = graph_repo.update_service_record(record_id, {"status": "accepted", "review_note": note})
    logger.info("Record %r accepted. Note: %r", record_id, note)
    return {"record_id": record_id, "status": "accepted", "record": updated}


# ---------------------------------------------------------------------------
# POST /api/maintenance/review-queue/{record_id}/reject
# ---------------------------------------------------------------------------

@router.post("/review-queue/{record_id}/reject")
def reject_record(
    record_id: str,
    body: RejectActionRequest,
    graph_repo=Depends(get_graph_repo),
):
    """Reject a queued record (status → rejected). Note is required."""
    sr = graph_repo.get_service_record(record_id)
    if sr is None:
        raise HTTPException(status_code=404, detail=f"Record {record_id!r} not found")
    updated = graph_repo.update_service_record(
        record_id, {"status": "rejected", "review_note": body.note}
    )
    logger.info("Record %r rejected. Note: %r", record_id, body.note)
    return {"record_id": record_id, "status": "rejected", "record": updated}


# ---------------------------------------------------------------------------
# GET /api/domains
# ---------------------------------------------------------------------------

@domains_router.get("/domains")
def get_domains():
    """Return all registered domain descriptors for the frontend switcher."""
    return list_domains()
