"""
backend/scripts/backfill_conflict_scores.py

H3: Backfill real confidence and routing across the ingested corpus.

Bulk ingestion writes records quickly but bypasses the LLM scoring engine to save
time. This script processes every record in chronological order, scoring it
against its asset's *prior* history (to avoid data leakage from the future),
and updates its confidence, status, and any SUPERSEDES edges.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path

from fastapi import HTTPException

# Add backend directory to sys.path so we can import modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import settings
from graph.neo4j_client import Neo4jClient
from graph.queries import GraphRepository
from services.conflict_engine import find_candidate_pairs, classify_conflict, process_record
from services.groq_service import GroqService
from api.routes.maintenance import _get_maintenance_adapter

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("backfill")

# Ensure UTF-8 output for Windows console
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

def main():
    parser = argparse.ArgumentParser(description="Backfill conflict scores")
    parser.add_argument("--limit", type=int, help="Limit number of records processed")
    parser.add_argument("--asset", action="append", help="Filter to specific tail numbers")
    parser.add_argument("--resume", action="store_true", help="Skip records that have already been scored (confidence != 1.0)")
    args = parser.parse_args()

    client = Neo4jClient(settings.NEO4J_URI, settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
    repo = GraphRepository(client)
    groq = GroqService(api_key=settings.GROQ_API_KEY, model=settings.GROQ_MODEL)
    
    if not groq.is_live:
        logger.warning("Groq is not live. Using cache and stubs.")
        # sys.exit(1)

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
        "llm_calls": 0,
        "parse_failures": 0,
        "supersedes_created": 0,
        "statuses": {"needs_review": 0, "auto_accepted": 0, "superseded": 0},
        "confidences": []
    }
    
    adapter = _get_maintenance_adapter()
    
    for rec in all_recs:
        record_id = rec.get("record_id") or rec.get("id")
        asset_id = rec.get("asset_id")
        
        conf = rec.get("confidence")
        if args.resume and conf is not None and conf != 1.0:
            stats["skipped_resume"] += 1
            continue
            
        logger.info(f"Processing {record_id} (Asset: {rec.get('tail_number')})")
        
        try:
            res = process_record(
                repo, groq, adapter, record_id,
                threshold=settings.MAINT_CONFIDENCE_THRESHOLD,
                allow_stub=True
            )
            stats["processed"] += 1
            stats["statuses"][res["status_applied"]] = stats["statuses"].get(res["status_applied"], 0) + 1
            stats["confidences"].append(res["confidence"])
            stats["llm_calls"] += res["candidates_considered"]
            stats["parse_failures"] += res.get("parse_failures", 0)
            if res["status_applied"] == "auto_accepted" and res.get("adjudication", {}).get("action") in ("supersedes", "partial_supersedes"):
                stats["supersedes_created"] += 1
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
    print(f"LLM/Cache Calls:    {stats['llm_calls']} (cache handles internally)")
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
