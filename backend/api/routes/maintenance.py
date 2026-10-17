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
import time
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field, field_validator

from agents.maintenance_agent import MaintenanceAgent
from api.deps import get_graph_repo, get_groq_service, get_settings
from api.routes.ops import _require_ops_token
from domains.registry import list_domains
from services.conflict_engine import MAINT_CONFIDENCE_THRESHOLD, process_record
from services.analysis_state import normalize_analysis_for_api
from services.analysis_budget import BudgetExhausted, DailyBudgetManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/maintenance", tags=["maintenance"])
domains_router = APIRouter(tags=["domains"])


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class IngestRequest(BaseModel):
    csv_path: str | None = None
    limit: int | None = Field(default=None, gt=0)


class RecordProcessRequest(BaseModel):
    record_id: str | None = None
    tail_number: str | None = None
    date: str | None = None
    part_name: str | None = None
    condition: str | None = None
    location: str | None = None
    jasc_code: str | None = None
    discrepancy: str | None = None
    threshold: float | None = Field(default=None, ge=0.0, le=1.0)


class ReviewActionRequest(BaseModel):
    note: str | None = None


class RejectActionRequest(BaseModel):
    note: str = Field(min_length=1)  # required for rejection

    @field_validator("note")
    @classmethod
    def note_must_explain_rejection(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("rejection note must not be blank")
        return value


class AnalysisRunRequest(BaseModel):
    batch_size: int = Field(default=10, ge=1, le=25)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_maintenance_adapter():
    from domains.registry import get_adapter
    return get_adapter("maintenance")


def _analysis_budget(settings) -> DailyBudgetManager:
    state_file = settings.MAINT_BUDGET_STATE_FILE or str(
        Path(settings.MAINT_DATA_DIR) / "analysis_budget.json"
    )
    return DailyBudgetManager(
        state_file,
        request_limit=settings.MAINT_DAILY_REQUEST_LIMIT,
        token_limit=settings.MAINT_DAILY_TOKEN_LIMIT,
        utilization=settings.MAINT_BUDGET_UTILIZATION,
        token_reserve=settings.MAINT_BUDGET_TOKEN_RESERVE,
    )


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
# GET /api/maintenance/records/{record_id} — read-only detail
# ---------------------------------------------------------------------------

@router.get("/records")
def list_records(
    asset_id: str | None = None,
    q: str | None = None,
    status: str | None = None,
    analysis_state: str | None = None,
    part: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    sort: Literal["occurred_at_desc", "occurred_at_asc", "record_id_asc", "record_id_desc"] = "occurred_at_desc",
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    graph_repo=Depends(get_graph_repo),
):
    """Fleet-wide record list with store-level filtering and pagination."""
    page = graph_repo.list_service_records_page(
        asset_id=asset_id, q=q, status=status, analysis_state=analysis_state,
        part=part, date_from=date_from, date_to=date_to, sort=sort,
        limit=limit, offset=offset,
    )
    page["items"] = [normalize_analysis_for_api(record) for record in page["items"]]
    return page


@router.get("/records/{record_id}")
def get_single_record(
    record_id: str,
    graph_repo=Depends(get_graph_repo),
    groq_service=Depends(get_groq_service),
    settings=Depends(get_settings),
):
    """
    Read-only fetch of a single record's conflict details. 
    Runs the engine in dry_run mode to fetch classification without mutating the graph.
    """
    adapter = _get_maintenance_adapter()
    try:
        result = process_record(
            graph_repo, groq_service, adapter, record_id,
            threshold=settings.MAINT_CONFIDENCE_THRESHOLD,
            allow_stub=False,
            dry_run=True
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
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
    Run conflict detection on an already-ingested record, or ingest and process a new one.
    """
    adapter = _get_maintenance_adapter()
    threshold = body.threshold if body.threshold is not None else settings.MAINT_CONFIDENCE_THRESHOLD

    record_id = body.record_id
    if body.tail_number:
        import datetime
        if not record_id:
            record_id = f"DEMO{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Inline ingestion
        raw = {
            "OperatorControlNumber": record_id,
            "RegistryNNumber": body.tail_number,
            "DifficultyDate": body.date,
            "PartName": body.part_name,
            "PartCondition": body.condition,
            "PartLocation": body.location,
            "JASCCode": body.jasc_code,
            "Discrepancy": body.discrepancy
        }
        agent = MaintenanceAgent(graph_repo, None)
        agent.run({"records": [raw]})

    if not record_id:
        raise HTTPException(status_code=422, detail="record_id is required if not providing a full record")

    try:
        result = process_record(
            graph_repo, groq_service, adapter, record_id,
            threshold=threshold, allow_stub=False,
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
    """List assets and record counts using one repository aggregation."""
    return graph_repo.list_assets_with_counts()


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

    return {
        "asset_id": asset_id,
        "records": [normalize_analysis_for_api(record) for record in history],
        "count": len(history),
    }


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


@router.get("/analysis/status")
def analysis_status(graph_repo=Depends(get_graph_repo)):
    """Return live conflict-analysis coverage from stored record metadata."""
    return graph_repo.analysis_status()


@router.post("/analysis/run")
def run_analysis_batch(
    body: AnalysisRunRequest | None = None,
    _: None = Depends(_require_ops_token),
    graph_repo=Depends(get_graph_repo),
    groq_service=Depends(get_groq_service),
    settings=Depends(get_settings),
):
    """Process the next bounded chronological batch of unscored records."""
    if not groq_service.is_live:
        raise HTTPException(status_code=503, detail="A live Groq model is required for conflict analysis.")
    body = body or AnalysisRunRequest()
    before = graph_repo.analysis_status()
    page = graph_repo.list_service_records_page(
        analysis_state="unscored", sort="occurred_at_asc",
        limit=body.batch_size, offset=0,
    )
    adapter = _get_maintenance_adapter()
    budget = _analysis_budget(settings)
    results = []
    model_records = 0
    screen_records = 0
    stopped_reason = None
    for record in page["items"]:
        record_id = record["record_id"]
        last_error = None
        for attempt in range(3):
            try:
                result = process_record(
                    graph_repo, groq_service, adapter, record_id,
                    threshold=settings.MAINT_CONFIDENCE_THRESHOLD,
                    allow_stub=False,
                    analysis_mode=settings.MAINT_ANALYSIS_MODE,
                    budget_manager=budget,
                )
                if result.get("analysis_method") in ("llm", "llm-escalated"):
                    model_records += 1
                elif result.get("analysis_method") == "screen":
                    screen_records += 1
                results.append({
                    "record_id": record_id,
                    "analysis_state": "needs_review" if result["status_applied"] == "needs_review" else "scored",
                    "classification_label": (result.get("classification") or {}).get("label"),
                    "confidence": result.get("confidence"),
                    "candidates_considered": result.get("candidates_considered", 0),
                    "analysis_method": result.get("analysis_method"),
                })
                last_error = None
                break
            except BudgetExhausted as exc:
                stopped_reason = exc.stopped_reason
                last_error = None
                break
            except RuntimeError as exc:
                last_error = exc
                if "429" not in str(exc) and "rate limit" not in str(exc).lower():
                    break
                if attempt < 2:
                    time.sleep(0.5 * (attempt + 1))
        if stopped_reason:
            break
        if last_error is not None:
            raise HTTPException(status_code=503, detail=f"Analysis stopped at {record_id}: {last_error}")
    after = graph_repo.analysis_status()
    return {
        "batch_size": body.batch_size,
        "processed": len(results),
        "model_records": model_records,
        "screen_records": screen_records,
        "no_candidate_records": sum(
            result["classification_label"] == "no_candidates" for result in results
        ),
        "stopped_reason": stopped_reason,
        "budget_remaining": budget.snapshot(groq_service.model),
        "remaining_unscored": after["unscored"],
        "before": before,
        "after": after,
        "results": results,
    }


@router.get("/corrections")
def corrections(
    asset_id: str | None = None,
    component_changed: bool | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    graph_repo=Depends(get_graph_repo),
):
    return graph_repo.list_corrections_page(
        asset_id=asset_id, component_changed=component_changed,
        date_from=date_from, date_to=date_to, limit=limit, offset=offset,
    )


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
    updated = graph_repo.update_service_record(
        record_id,
        {"status": "accepted", "analysis_state": "reviewed", "review_note": note},
    )
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
    if sr.get("status") not in ("needs_review", "auto_accepted"):
        raise HTTPException(
            status_code=409,
            detail=f"Record {record_id!r} is in status '{sr.get('status')}', cannot reject",
        )
    updated = graph_repo.update_service_record(
        record_id,
        {"status": "rejected", "analysis_state": "reviewed", "review_note": body.note},
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
