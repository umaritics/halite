"""
evaluate_conflict_detection.py — T7 Evaluation Harness for the maintenance domain.

This script runs the conflict engine against the ground truth dataset,
measuring precision, recall, and the performance curve across confidence thresholds.

Rules from §T7:
1. Strip the "SUPPLEMENTAL REPORT FOR" citation before running.
2. Compare against baseline (most-recent-prior).
3. Sweep threshold from 0.50 to 0.95.
4. Emit docs/evaluation_results.csv and docs/evaluation_results.md.
5. Abort if groq_service is not live.
"""
import csv
import logging
import os
import re
import sys
from pathlib import Path

# Setup paths for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from config import settings
from domains.registry import get_adapter
from graph.memory_store import MemoryGraphStore
from graph.neo4j_client import Neo4jClient
from graph.queries import GraphRepository
from services.conflict_engine import process_record
from services.groq_service import GroqService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_app_state():
    """Initialize Groq and Graph. Abort if Groq is not live."""
    groq_service = GroqService(
        settings.GROQ_API_KEY,
        settings.GROQ_MODEL,
        demo_mode=not settings.groq_configured,
    )

    if not groq_service.is_live:
        logger.error("evaluate_conflict_detection: groq_service is not live.")
        logger.error("You must have GROQ_API_KEY set to run the evaluation harness.")
        sys.exit(1)

    # Use whatever graph is configured
    use_demo = settings.DEMO_MODE or not settings.neo4j_configured
    if use_demo:
        store = MemoryGraphStore()
        graph_repo = GraphRepository(store)
    else:
        store = Neo4jClient(
            settings.NEO4J_URI,
            settings.NEO4J_USERNAME,
            settings.NEO4J_PASSWORD,
            database=settings.NEO4J_DATABASE,
        )
        graph_repo = GraphRepository(store)

    adapter = get_adapter("maintenance")
    
    # Ensure data is ingested (critical for MemoryGraphStore in DEMO_MODE)
    records = graph_repo.list_service_records()
    if len(records) == 0:
        logger.info("Graph is empty. Ingesting POC corpus before evaluation...")
        from agents.maintenance_agent import MaintenanceAgent
        agent = MaintenanceAgent(graph_repo, None)
        corpus_path = str(Path("data/processed/sdr_poc_corpus.csv"))
        res = agent.run({"csv_path": corpus_path})
        logger.info(f"Ingested: {res}")

    return graph_repo, groq_service, adapter


def strip_citation(text: str) -> str:
    """
    Strip SUPPLEMENTAL REPORT FOR (...) from text.
    §T7 requirement: leaving it in means the system reads the answer key.
    """
    pattern = re.compile(r"SUPPLEMENTAL\s+REPORT\s+FOR\s*\(?\s*[A-Z0-9]{6,}\s*\)?", re.IGNORECASE)
    stripped = pattern.sub("", text)
    return stripped


import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--balanced", action="store_true")
    parser.add_argument("--sweep", action="store_true")
    args = parser.parse_args()

    # Create app context
    graph_repo, groq_service, adapter = init_app_state()

    # Load ground truth
    gt_path = Path("data/processed/ground_truth_pairs.csv")
    if not gt_path.exists():
        logger.error(f"Ground truth file not found: {gt_path}")
        sys.exit(1)

    gt_df = pd.read_csv(gt_path)
    if len(gt_df) == 0:
        logger.error("Ground truth file is empty.")
        sys.exit(1)

    # Also we need to evaluate false-conflict rate on records with NO ground truth.
    # We will sample some records that are NOT in superseding_record_id.
    all_superseding = set(gt_df["superseding_record_id"])
    all_records = graph_repo.list_service_records()
    all_record_ids = [r["record_id"] for r in all_records]

    # Find negative samples
    negative_samples = []
    if args.balanced:
        # Sample records that: (a) belong to an asset with at least 3 prior records, 
        # (b) appear in no ground-truth pair, 
        # (c) contain no supplemental-report citation and no WILL BE SUBMITTED open marker.
        import random
        random.seed(42)
        all_records_shuffled = list(all_records)
        random.shuffle(all_records_shuffled)
        
        for r in all_records_shuffled:
            if r["record_id"] in all_superseding:
                continue
            
            text = r.get("text", "").upper()
            if "SUPPLEMENTAL REPORT FOR" in text or "WILL BE SUBMITTED" in text:
                continue
                
            asset_id = None
            for e in graph_repo.store.edges:
                if e["source"] == r["id"] and e["type"] == "ABOUT":
                    asset_id = e["target"]
                    break
                    
            if not asset_id:
                continue
                
            history = graph_repo.list_asset_history(asset_id, limit=200)
            older = [x for x in history if x["occurred_at"] <= r["occurred_at"] and x["record_id"] != r["record_id"]]
            
            if len(older) >= 3:
                negative_samples.append(r["record_id"])
                if len(negative_samples) >= len(gt_df):
                    break

    logger.info(f"Loaded {len(gt_df)} ground truth pairs and {len(negative_samples)} negative samples.")

    results_gt = []
    
    # Process positive ground truth pairs
    for _, row in gt_df.iterrows():
        superseding_id = row["superseding_record_id"]
        superseded_id = row["superseded_record_id"]

        sr = graph_repo.get_service_record(superseding_id)
        if not sr:
            logger.warning(f"Record {superseding_id} not found in graph. Skipping.")
            continue
        
        original_text = sr.get("text", "")
        stripped_text = strip_citation(original_text)
        
        if original_text == stripped_text and "SUPPLEMENTAL REPORT FOR" in original_text.upper():
            logger.error(f"Failed to strip citation from {superseding_id}: {original_text}")
            sys.exit(1)

        # Apply stripped text to graph temporarily for the test
        graph_repo.update_service_record(superseding_id, {"text": stripped_text})

        # Run process_record with a low threshold so we get the raw confidence
        try:
            res = process_record(graph_repo, groq_service, adapter, superseding_id, threshold=0.0)
        except Exception as e:
            logger.error(f"process_record failed on {superseding_id}: {e}")
            continue

        # Restore original text
        graph_repo.update_service_record(superseding_id, {"text": original_text})

        # Baseline: most-recent-prior-record-on-same-asset
        asset_id = None
        for e in graph_repo.store.edges:
            if e["source"] == sr["id"] and e["type"] == "ABOUT":
                asset_id = e["target"]
                break
        history = graph_repo.list_asset_history(asset_id, limit=200) if asset_id else []
        older = []
        for x in history:
            if x["record_id"] == superseding_id:
                continue
            if x["occurred_at"] < sr["occurred_at"]:
                older.append(x)
            elif x["occurred_at"] == sr["occurred_at"] and x.get("submitted_at", "") < sr.get("submitted_at", ""):
                older.append(x)
                
        older.sort(key=lambda x: (x["occurred_at"], x.get("submitted_at", "")), reverse=True)
        baseline_pred_id = older[0]["record_id"] if older else None

        results_gt.append({
            "record_id": superseding_id,
            "true_prior_id": superseded_id,
            "pred_prior_id": res["best_prior"]["record_id"] if res["best_prior"] else None,
            "baseline_prior_id": baseline_pred_id,
            "confidence": res["confidence"],
            "action": res["adjudication"]["action"] if res["adjudication"] else "no_action",
            "is_gt": True
        })

    results_neg = []
    # Process negative samples
    for neg_id in negative_samples:
        try:
            res = process_record(graph_repo, groq_service, adapter, neg_id, threshold=0.0)
            results_neg.append({
                "record_id": neg_id,
                "confidence": res["confidence"],
                "action": res["adjudication"]["action"] if res["adjudication"] else "no_action",
                "is_gt": False
            })
        except Exception as e:
            logger.error(f"process_record failed on negative sample {neg_id}: {e}")
            continue

    if not results_gt:
        logger.error("No ground truth pairs processed.")
        sys.exit(1)

    n_gt = len(results_gt)
    n_neg = len(results_neg)

    # C2: Partitions
    # Easy: baseline_prior_id == true_prior_id
    # Hard: baseline_prior_id != true_prior_id
    easy_gt = [r for r in results_gt if r["baseline_prior_id"] == r["true_prior_id"]]
    hard_gt = [r for r in results_gt if r["baseline_prior_id"] != r["true_prior_id"]]
    
    logger.info(f"Partitions: Easy N={len(easy_gt)}, Hard N={len(hard_gt)}")

    def compute_metrics(threshold, include_negatives=False):
        # We compute for baseline and engine.
        # For engine, a positive prediction is when confidence >= threshold AND action is supersedes/partial
        
        # Positive Set
        # Engine true positive: pred_prior == true_prior AND conf >= t AND action supersedes
        # Baseline true positive: baseline_prior == true_prior
        engine_tp = sum(1 for r in results_gt if r["confidence"] >= threshold and r["pred_prior_id"] == r["true_prior_id"] and r["action"] in ("supersedes", "partial_supersedes"))
        baseline_tp = sum(1 for r in results_gt if r["baseline_prior_id"] == r["true_prior_id"])
        
        engine_fn = n_gt - engine_tp
        baseline_fn = n_gt - baseline_tp
        
        # Negative Set (only if include_negatives)
        engine_fp = 0
        baseline_fp = 0
        if include_negatives and n_neg > 0:
            # Engine false positive: conf >= t AND action supersedes
            engine_fp = sum(1 for r in results_neg if r["confidence"] >= threshold and r["action"] in ("supersedes", "partial_supersedes"))
            # Baseline false positive: baseline_prior_id is not None
            # Wait, baseline always picks the most recent. On negative set, baseline ALWAYs picks something.
            # But the negative set elements are guaranteed to have at least 3 prior records.
            # So baseline ALWAYS produces a conflict.
            baseline_fp = n_neg
            
        # Precision = TP / (TP + FP)
        engine_prec = engine_tp / (engine_tp + engine_fp) if (engine_tp + engine_fp) > 0 else 0.0
        baseline_prec = baseline_tp / (baseline_tp + baseline_fp) if (baseline_tp + baseline_fp) > 0 else 0.0
        
        # Recall = TP / (TP + FN)  -> same as accuracy on positives
        engine_rec = engine_tp / n_gt if n_gt > 0 else 0.0
        baseline_rec = baseline_tp / n_gt if n_gt > 0 else 0.0
        
        # F1
        engine_f1 = 2 * (engine_prec * engine_rec) / (engine_prec + engine_rec) if (engine_prec + engine_rec) > 0 else 0.0
        baseline_f1 = 2 * (baseline_prec * baseline_rec) / (baseline_prec + baseline_rec) if (baseline_prec + baseline_rec) > 0 else 0.0
        
        # False Conflict Rate
        engine_fcr = engine_fp / n_neg if n_neg > 0 else 0.0
        baseline_fcr = baseline_fp / n_neg if n_neg > 0 else 0.0
        
        # Coverage
        engine_auto_accepted = sum(1 for r in results_gt if r["confidence"] >= threshold) + sum(1 for r in results_neg if r["confidence"] >= threshold)
        engine_coverage = engine_auto_accepted / (n_gt + n_neg) if (n_gt + n_neg) > 0 else 0.0
        
        # Precision within auto-accepted subset
        # Auto-accepted positives that are TP
        aa_tp = sum(1 for r in results_gt if r["confidence"] >= threshold and r["pred_prior_id"] == r["true_prior_id"] and r["action"] in ("supersedes", "partial_supersedes"))
        aa_fp = sum(1 for r in results_gt if r["confidence"] >= threshold and not (r["pred_prior_id"] == r["true_prior_id"] and r["action"] in ("supersedes", "partial_supersedes"))) + engine_fp
        
        aa_prec = aa_tp / (aa_tp + aa_fp) if (aa_tp + aa_fp) > 0 else 0.0
        
        return {
            "engine": {"precision": engine_prec, "recall": engine_rec, "f1": engine_f1, "fcr": engine_fcr, "coverage": engine_coverage, "aa_prec": aa_prec},
            "baseline": {"precision": baseline_prec, "recall": baseline_rec, "f1": baseline_f1, "fcr": baseline_fcr}
        }
        
    metrics = compute_metrics(0.72, include_negatives=args.balanced)
    
    # Save sweep results
    import csv
    docs_dir = Path("../docs")
    docs_dir.mkdir(exist_ok=True)
    csv_path = docs_dir / "evaluation_results.csv"
    md_path = docs_dir / "evaluation_results.md"
    
    thresholds = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95]
    sweep_results = []
    if args.sweep:
        for t in thresholds:
            m = compute_metrics(t, include_negatives=args.balanced)["engine"]
            # routed to review: everything not auto-accepted
            routed = (n_gt + n_neg) - (sum(1 for r in results_gt if r["confidence"] >= t) + sum(1 for r in results_neg if r["confidence"] >= t))
            sweep_results.append({
                "threshold": t,
                "coverage": m["coverage"],
                "precision": m["aa_prec"],
                "routed": routed
            })
            
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["threshold", "coverage", "precision", "routed"])
            writer.writeheader()
            writer.writerows(sweep_results)

    # Write Markdown Report
    with open(md_path, "w") as f:
        f.write("# Halite Maintenance Domain - Conflict Engine Evaluation\n\n")
        f.write("This report details the evaluation of the maintenance conflict engine against ground-truth FAA SDRs.\n")
        f.write("The explicit citations ('SUPPLEMENTAL REPORT FOR...') were stripped from the superseding records before processing.\n\n")
        
        f.write("## Overall Metrics\n")
        f.write(f"- **Ground truth pairs evaluated (N):** {n_gt}\n")
        f.write(f"- **Negative samples evaluated (N):** {n_neg}\n")
        
        if args.balanced:
            f.write(f"- **Baseline Precision:** {metrics['baseline']['precision']:.3f}\n")
            f.write(f"- **Baseline Recall:** {metrics['baseline']['recall']:.3f}\n")
            f.write(f"- **Baseline F1:** {metrics['baseline']['f1']:.3f}\n")
            f.write(f"- **Baseline False Conflict Rate:** {metrics['baseline']['fcr']:.3f}\n")
            
            f.write(f"- **Engine Precision:** {metrics['engine']['precision']:.3f}\n")
            f.write(f"- **Engine Recall:** {metrics['engine']['recall']:.3f}\n")
            f.write(f"- **Engine F1:** {metrics['engine']['f1']:.3f}\n")
            f.write(f"- **Engine False Conflict Rate:** {metrics['engine']['fcr']:.3f}\n")
            
        f.write(f"- **Automation Coverage:** {metrics['engine']['coverage']:.3f}\n")
        f.write(f"- **Auto-Accepted Precision:** {metrics['engine']['aa_prec']:.3f}\n\n")
        
        f.write("## Partitions\n")
        f.write(f"- **Easy Partition (N={len(easy_gt)}):** Baseline correctly picked the prior record.\n")
        f.write(f"- **Hard Partition (N={len(hard_gt)}):** There were intervening records.\n")
        
        # Re-compute for partitions
        if len(easy_gt) > 0:
            e_tp = sum(1 for r in easy_gt if r["confidence"] >= 0.72 and r["pred_prior_id"] == r["true_prior_id"] and r["action"] in ("supersedes", "partial_supersedes"))
            f.write(f"- **Engine Recall on Easy:** {e_tp / len(easy_gt):.3f}\n")
        if len(hard_gt) > 0:
            h_tp = sum(1 for r in hard_gt if r["confidence"] >= 0.72 and r["pred_prior_id"] == r["true_prior_id"] and r["action"] in ("supersedes", "partial_supersedes"))
            f.write(f"- **Engine Recall on Hard:** {h_tp / len(hard_gt):.3f}\n\n")

        if args.sweep:
            f.write("## Threshold Sweep\n\n")
            f.write("| Threshold | Automation Coverage | Auto-Accepted Precision | Routed to Review |\n")
            f.write("|---|---|---|---|\n")
            for sr in sweep_results:
                f.write(f"| {sr['threshold']:.2f} | {sr['coverage']:.3f} | {sr['precision']:.3f} | {sr['routed']} |\n")
                
        f.write("\n## Limitations\n")
        f.write("- Negative labels are weak (absence of an author-recorded link is not proof of no conflict).\n")
        f.write("- N is small and corpus is only one year of one dataset.\n")
        f.write("- Classifier is an external hosted model.\n")

    logger.info(f"Evaluation complete. Results written to {csv_path} and {md_path}")

if __name__ == "__main__":
    main()
