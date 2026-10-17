"""
backend/scripts/backfill_conflict_scores.py

H3: Backfill real confidence and routing across the ingested corpus.

Bulk ingestion writes records quickly but bypasses the LLM scoring engine to save
time. This script processes every record in chronological order, scoring it
against its asset's *prior* history (to avoid data leakage from the future),
and updates its confidence, status, and any SUPERSEDES edges.
"""

import argparse
import logging
import os
import sys
import time
from pathlib import Path

# Add backend directory to sys.path so we can import modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import settings
from graph.neo4j_client import Neo4jClient
from graph.queries import GraphRepository
from services.conflict_engine import process_record
from services.groq_service import GroqService
from services.analysis_budget import BudgetExhausted, DailyBudgetManager
from api.routes.maintenance import _get_maintenance_adapter

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("backfill")

# Ensure UTF-8 output for Windows console
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')


def _is_unscored_placeholder(record: dict) -> bool:
    """Resume is driven by the explicit analysis state, never confidence."""
    return (record.get("analysis_state") or "unscored") == "unscored"


def _process_with_retries(repo, groq, adapter, record_id: str, *, budget=None, attempts: int = 3):
    last_error = None
    for attempt in range(attempts):
        try:
            return process_record(
                repo, groq, adapter, record_id,
                threshold=settings.MAINT_CONFIDENCE_THRESHOLD,
                allow_stub=False,
                analysis_mode=settings.MAINT_ANALYSIS_MODE,
                budget_manager=budget,
            )
        except RuntimeError as exc:
            last_error = exc
            if "429" not in str(exc) and "rate limit" not in str(exc).lower():
                raise
            if attempt + 1 < attempts:
                time.sleep(0.5 * (attempt + 1))
    raise last_error

def main():
    parser = argparse.ArgumentParser(description="Backfill conflict scores")
    parser.add_argument("--limit", type=int, help="Limit number of records processed")
    parser.add_argument("--asset", action="append", help="Filter to specific tail numbers")
    parser.add_argument("--resume", action="store_true", help="Process only records with analysis_state=unscored")
    parser.add_argument(
        "--until-budget", action="store_true",
        help="Resume unscored records and stop cleanly at the persistent daily budget",
    )
    args = parser.parse_args()

    client = Neo4jClient(settings.NEO4J_URI, settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
    repo = GraphRepository(client)
    groq = GroqService(api_key=settings.GROQ_API_KEY, model=settings.GROQ_MODEL)
    budget_path = settings.MAINT_BUDGET_STATE_FILE or str(
        Path(settings.MAINT_DATA_DIR) / "analysis_budget.json"
    )
    budget = DailyBudgetManager(
        budget_path,
        request_limit=settings.MAINT_DAILY_REQUEST_LIMIT,
        token_limit=settings.MAINT_DAILY_TOKEN_LIMIT,
        utilization=settings.MAINT_BUDGET_UTILIZATION,
        token_reserve=settings.MAINT_BUDGET_TOKEN_RESERVE,
    )
    
    if not groq.is_live:
        logger.error("Groq is not live. Refusing to backfill with cache or stubs.")
        sys.exit(1)

    # 1. Fetch all records, optionally filtered by asset
    logger.info("Fetching all service records...")
    all_recs = []
    
    if args.asset:
        for tail in args.asset:
            try:
                with client.driver.session() as session:
                    res = session.run("MATCH (a:Asset {tail_number: $tail}) RETURN a.id as id", tail=tail).data()
                    if not res:
                        logger.warning(f"Asset {tail} not found")
                        continue
                    history = repo.list_asset_history(res[0]["id"])
                    all_recs.extend(history)
            except Exception as e:
                logger.error(f"Failed to fetch asset {tail}: {e}")
    else:
        # Fetch all records from all assets by querying neo4j directly
        try:
            with client.driver.session() as session:
                res = session.run("""
                    MATCH (r:ServiceRecord)-[:ABOUT]->(a:Asset)
                    RETURN r, a.id AS asset_id, a.tail_number AS tail_number
                """)
                for record in res:
                    r_dict = dict(record["r"].items())
                    r_dict["asset_id"] = record["asset_id"]
                    r_dict["tail_number"] = record["tail_number"]
                    all_recs.append(r_dict)
        except Exception as e:
            logger.error(f"Failed to fetch records: {e}")
            sys.exit(1)
            
    if not all_recs:
        logger.error("No records found to process.")
        sys.exit(1)
        
    # Sort chronologically by date
    def parse_date(date_str):
        try:
            return time.strptime(date_str.split("T")[0], "%Y-%m-%d")
        except:
            return time.strptime("1970-01-01", "%Y-%m-%d")

    all_recs.sort(key=lambda x: parse_date(x.get("occurred_at", "1970-01-01")))
    
    if args.limit:
        all_recs = all_recs[:args.limit]

    logger.info(f"Loaded {len(all_recs)} records to process.")
    
    stats = {
        "processed": 0,
        "skipped_resume": 0,
        "cache_hits": 0,
        "model_classifications": 0,
        "screen_records": 0,
        "provider_requests": 0,
        "parse_failures": 0,
        "supersedes_created": 0,
        "statuses": {"needs_review": 0, "auto_accepted": 0, "no_action": 0, "superseded": 0},
        "confidences": []
    }
    
    adapter = _get_maintenance_adapter()
    
    for rec in all_recs:
        record_id = rec.get("record_id") or rec.get("id")
        asset_id = rec.get("asset_id")
        
        if (args.resume or args.until_budget) and not _is_unscored_placeholder(rec):
            stats["skipped_resume"] += 1
            continue
            
        logger.info(f"Processing {record_id} (Asset: {rec.get('tail_number')})")
        
        try:
            res = _process_with_retries(repo, groq, adapter, record_id, budget=budget)
            stats["processed"] += 1
            stats["statuses"][res["status_applied"]] = stats["statuses"].get(res["status_applied"], 0) + 1
            stats["confidences"].append(res["confidence"])
            method = res.get("analysis_method")
            stats["model_classifications"] += int(method in ("llm", "llm-escalated"))
            stats["screen_records"] += int(method == "screen")
            classification = res.get("classification") or {}
            if not classification.get("cache_hit"):
                stats["provider_requests"] += int(classification.get("passes") or 0)
            stats["parse_failures"] += res.get("parse_failures", 0)
            if res["status_applied"] == "auto_accepted" and res.get("adjudication", {}).get("action") in ("supersedes", "partial_supersedes"):
                stats["supersedes_created"] += 1
        except BudgetExhausted as exc:
            stats["stopped_reason"] = exc.stopped_reason
            logger.info("Stopped cleanly at %s", exc.stopped_reason)
            break
        except Exception as e:
            logger.error(f"Failed to process {record_id}: {e}")
            continue
        
        time.sleep(0.1)

    # 6. Report
    print("\n" + "="*50)
    print("BACKFILL COMPLETE")
    print("="*50)
    print(f"Records processed:  {stats['processed']}")
    print(f"Records skipped:    {stats['skipped_resume']}")
    print(f"Parse failures:     {stats['parse_failures']}")
    print(f"SUPERSEDES created: {stats['supersedes_created']}")
    print(f"Model classifications: {stats['model_classifications']}")
    print(f"Screen records:        {stats['screen_records']}")
    print(f"Provider requests:     {stats['provider_requests']} (cache hits excluded)")
    print(f"Stopped reason:     {stats.get('stopped_reason') or 'none'}")
    print(f"Budget remaining:   {budget.snapshot(groq.model)}")
    print("\nStatus Distribution:")
    for st, count in stats["statuses"].items():
        print(f"  {st}: {count}")
        
    confs = stats["confidences"]
    if confs:
        print("\nConfidence Stats:")
        print(f"  Min:    {min(confs):.4f}")
        confs.sort()
        print(f"  Median: {confs[len(confs)//2]:.4f}")
        print(f"  Max:    {max(confs):.4f}")

if __name__ == "__main__":
    main()
