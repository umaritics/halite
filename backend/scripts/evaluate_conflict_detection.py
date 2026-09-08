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


def run_evaluation():
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

    # Find negative samples (records not in ground truth as superseding, but have prior history)
    negative_samples = []
    for r in all_records:
        if r["record_id"] not in all_superseding:
            asset_id = None
            for e in graph_repo.store.edges:
                if e["source"] == r["id"] and e["type"] == "ABOUT":
                    asset_id = e["target"]
                    break
            # Must have prior history on the same asset to be a valid negative test
            history = graph_repo.list_asset_history(asset_id, limit=200)
            older = [x for x in history if x["occurred_at"] <= r["occurred_at"] and x["record_id"] != r["record_id"]]
            if older:
                negative_samples.append(r["record_id"])
                if len(negative_samples) >= len(gt_df):  # Balance the set
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
        history = graph_repo.list_asset_history(sr.get("asset_key", ""), limit=200)
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
    sample_warn = " SMALL SAMPLE — indicative only" if n_gt < 30 else ""

    # Metric: Baseline detection accuracy
    baseline_correct = sum(1 for r in results_gt if r["pred_prior_id"] == r["baseline_prior_id"] and r["baseline_prior_id"] == r["true_prior_id"])
    baseline_acc = baseline_correct / n_gt

    # Metric: Detection accuracy (did it pick the right prior record out of the candidate pool?)
    detection_correct = sum(1 for r in results_gt if r["pred_prior_id"] == r["true_prior_id"])
    detection_acc = detection_correct / n_gt

    # Metric: Adjudication accuracy (did it realize it supersedes?)
    adjudication_correct = sum(1 for r in results_gt if r["pred_prior_id"] == r["true_prior_id"] and r["action"] in ("supersedes", "partial_supersedes"))
    adjudication_acc = adjudication_correct / n_gt

    # Sweep threshold
    thresholds = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95]
    sweep_results = []

    for t in thresholds:
        # True positives: GT pair with confidence >= t and correct prior and action supersedes
        tp = sum(1 for r in results_gt if r["confidence"] >= t and r["pred_prior_id"] == r["true_prior_id"] and r["action"] in ("supersedes", "partial_supersedes"))
        
        # False Positives:
        # 1. GT pair with confidence >= t but WRONG prior OR action is not supersedes
        # 2. Negative sample with confidence >= t and action is supersedes
        fp_gt = sum(1 for r in results_gt if r["confidence"] >= t and (r["pred_prior_id"] != r["true_prior_id"] or r["action"] not in ("supersedes", "partial_supersedes")))
        fp_neg = sum(1 for r in results_neg if r["confidence"] >= t and r["action"] in ("supersedes", "partial_supersedes"))
        fp = fp_gt + fp_neg
        
        # False Negatives: GT pair with confidence < t
        fn = sum(1 for r in results_gt if r["confidence"] < t)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        
        auto_accepted_gt = sum(1 for r in results_gt if r["confidence"] >= t)
        auto_accepted_neg = sum(1 for r in results_neg if r["confidence"] >= t)
        total_auto = auto_accepted_gt + auto_accepted_neg
        total_records = n_gt + n_neg
        automation_coverage = total_auto / total_records if total_records > 0 else 0.0

        false_conflict_rate = fp_neg / n_neg if n_neg > 0 else 0.0

        sweep_results.append({
            "threshold": f"{t:.2f}",
            "precision": f"{precision:.3f}",
            "recall": f"{recall:.3f}",
            "automation_coverage": f"{automation_coverage:.3f}",
            "false_conflict_rate": f"{false_conflict_rate:.3f}"
        })

    # Write CSV
    docs_dir = Path("../docs")
    docs_dir.mkdir(exist_ok=True)
    
    csv_path = docs_dir / "evaluation_results.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["threshold", "precision", "recall", "automation_coverage", "false_conflict_rate"])
        writer.writeheader()
        writer.writerows(sweep_results)

    # Write Markdown
    md_path = docs_dir / "evaluation_results.md"
    with open(md_path, "w") as f:
        f.write("# Halite Maintenance Domain — Conflict Engine Evaluation\n\n")
        f.write("This report details the evaluation of the maintenance conflict engine against ground-truth FAA SDRs.\n")
        f.write("The explicit citations ('SUPPLEMENTAL REPORT FOR...') were stripped from the superseding records before processing.\n\n")
        
        f.write("## Overall Metrics\n")
        f.write(f"- **Ground truth pairs evaluated (N):** {n_gt}{sample_warn}\n")
        f.write(f"- **Negative samples evaluated (N):** {n_neg}{sample_warn}\n")
        f.write(f"- **Baseline (most-recent) detection accuracy:** {baseline_acc:.1%} (N={n_gt})\n")
        f.write(f"- **Engine detection accuracy:** {detection_acc:.1%} (N={n_gt})\n")
        f.write(f"- **Engine adjudication accuracy:** {adjudication_acc:.1%} (N={n_gt})\n\n")

        f.write("## Threshold Sweep\n\n")
        f.write("| Threshold | Precision | Recall | Automation Coverage | False Conflict Rate |\n")
        f.write("|---|---|---|---|---|\n")
        for sr in sweep_results:
            f.write(f"| {sr['threshold']} | {sr['precision']} | {sr['recall']} | {sr['automation_coverage']} | {sr['false_conflict_rate']} |\n")
        
        f.write("\n\n*Note: Precision within the auto-accepted subset is listed in the Precision column.*")

    logger.info(f"Evaluation complete. Results written to {csv_path} and {md_path}")

if __name__ == "__main__":
    run_evaluation()
