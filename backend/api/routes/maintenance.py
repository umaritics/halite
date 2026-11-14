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
import datetime
import logging
import os
import time
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel, Field, field_validator

from agents.maintenance_agent import MaintenanceAgent
from api.deps import get_graph_repo, get_groq_service, get_rel_store, get_settings
from api.security import (
    AuthPrincipal,
    get_client_ip,
    require_llm_rate_limit,
    require_ops_or_admin,
    require_roles,
)
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


def _resolve_safe_csv_path(raw_path: str | None, settings) -> Path:
    """
    Restrict server-side CSV ingest strictly to `MAINT_DATA_DIR` or `tests/fixtures`
    so callers cannot traverse the host/container filesystem (`../../.env`, `/etc/*`).
    """
    backend_root = Path(__file__).resolve().parents[2]
    data_root = Path(settings.MAINT_DATA_DIR)
    if not data_root.is_absolute():
        data_root = (Path.cwd() / data_root).resolve()
    else:
        data_root = data_root.resolve()

    allowed_roots = (
        data_root,
        (backend_root / "data").resolve(),
        (backend_root / "tests" / "fixtures").resolve(),
    )

    candidate = (
        Path(raw_path)
        if raw_path
        else data_root / "processed" / "sdr_poc_corpus.csv"
    )
    if not candidate.is_absolute():
        candidate = (Path.cwd() / candidate).resolve()
    else:
        candidate = candidate.resolve()

    if candidate.suffix.lower() != ".csv" or not any(
        candidate.is_relative_to(root) for root in allowed_roots
    ):
        raise HTTPException(
            status_code=400,
            detail="csv_path must reference a .csv file inside the configured data or fixtures directory.",
        )

    return candidate


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
    Ingest FAA SDR records from a server-side CSV file inside `MAINT_DATA_DIR`
    or `tests/fixtures`.

    Body (JSON): {"csv_path": str, "limit": int | None}

    Returns real counts from the ingestion run.
    """
    if body is None:
        body = IngestRequest()

    resolved_csv = _resolve_safe_csv_path(body.csv_path, settings)
    if not resolved_csv.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"CSV file not found: {resolved_csv.name}. Run scripts/fetch_sdr_data.py first.",
        )

    payload: dict[str, Any] = {"csv_path": str(resolved_csv)}
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


@router.get("/records/{record_id}", dependencies=[Depends(require_llm_rate_limit)])
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

@router.post("/records", dependencies=[Depends(require_llm_rate_limit)])
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
    _: None = Depends(require_ops_or_admin),
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


def _record_review_audit(
    rel_store,
    request: Request,
    principal: AuthPrincipal,
    *,
    action: str,
    record_id: str,
    previous_status: str | None,
    note: str,
) -> None:
    if rel_store is None or not rel_store.is_available:
        return
    from services.auth_service import record_audit_event

    try:
        with rel_store.session_scope() as db:
            record_audit_event(
                db,
                action=action,
                organization_id=principal.organization_id,
                actor_user_id=principal.user_id if principal.kind == "user" else None,
                actor_email=principal.email,
                actor_role=principal.role,
                target_type="service_record",
                target_id=record_id,
                metadata={"previous_status": previous_status, "note": note},
                ip_address=get_client_ip(request),
            )
    except Exception as exc:
        logger.warning("Failed to persist review audit event for %s: %s", record_id, exc)


# ---------------------------------------------------------------------------
# POST /api/maintenance/review-queue/{record_id}/accept
# ---------------------------------------------------------------------------

@router.post("/review-queue/{record_id}/accept")
def accept_record(
    record_id: str,
    request: Request,
    body: ReviewActionRequest | None = None,
    principal: AuthPrincipal = Depends(require_roles("supervisor", "admin")),
    graph_repo=Depends(get_graph_repo),
    rel_store=Depends(get_rel_store),
):
    """Accept a queued record (status → accepted). Requires supervisor or admin role."""
    note = (body.note if body else None) or ""
    sr = graph_repo.get_service_record(record_id)
    if sr is None:
        raise HTTPException(status_code=404, detail=f"Record {record_id!r} not found")
    prev_status = sr.get("status")
    if prev_status not in ("needs_review", "auto_accepted"):
        raise HTTPException(
            status_code=409,
            detail=f"Record {record_id!r} is in status '{prev_status}', cannot accept",
        )
    reviewed_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    updated = graph_repo.update_service_record(
        record_id,
        {
            "status": "accepted",
            "analysis_state": "reviewed",
            "review_note": note,
            "reviewed_by_id": principal.user_id or "",
            "reviewed_by_name": principal.full_name,
            "reviewed_by_email": principal.email or "",
            "reviewed_by_role": principal.role,
            "reviewed_at": reviewed_at,
        },
    )
    _record_review_audit(
        rel_store,
        request,
        principal,
        action="maintenance.review.accepted",
        record_id=record_id,
        previous_status=prev_status,
        note=note,
    )
    logger.info("Record %r accepted by %s (%s). Note: %r", record_id, principal.email or principal.user_id, principal.role, note)
    return {"record_id": record_id, "status": "accepted", "record": updated}


# ---------------------------------------------------------------------------
# POST /api/maintenance/review-queue/{record_id}/reject
# ---------------------------------------------------------------------------

@router.post("/review-queue/{record_id}/reject")
def reject_record(
    record_id: str,
    body: RejectActionRequest,
    request: Request,
    principal: AuthPrincipal = Depends(require_roles("supervisor", "admin")),
    graph_repo=Depends(get_graph_repo),
    rel_store=Depends(get_rel_store),
):
    """Reject a queued record (status → rejected). Note is required. Requires supervisor or admin role."""
    sr = graph_repo.get_service_record(record_id)
    if sr is None:
        raise HTTPException(status_code=404, detail=f"Record {record_id!r} not found")
    prev_status = sr.get("status")
    if prev_status not in ("needs_review", "auto_accepted"):
        raise HTTPException(
            status_code=409,
            detail=f"Record {record_id!r} is in status '{prev_status}', cannot reject",
        )
    reviewed_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    updated = graph_repo.update_service_record(
        record_id,
        {
            "status": "rejected",
            "analysis_state": "reviewed",
            "review_note": body.note,
            "reviewed_by_id": principal.user_id or "",
            "reviewed_by_name": principal.full_name,
            "reviewed_by_email": principal.email or "",
            "reviewed_by_role": principal.role,
            "reviewed_at": reviewed_at,
        },
    )
    _record_review_audit(
        rel_store,
        request,
        principal,
        action="maintenance.review.rejected",
        record_id=record_id,
        previous_status=prev_status,
        note=body.note,
    )
    logger.info("Record %r rejected by %s (%s). Note: %r", record_id, principal.email or principal.user_id, principal.role, body.note)
    return {"record_id": record_id, "status": "rejected", "record": updated}


# ---------------------------------------------------------------------------
# GET /api/domains
# ---------------------------------------------------------------------------

@domains_router.get("/domains")
def get_domains():
    """Return all registered domain descriptors for the frontend switcher."""
    return list_domains()
