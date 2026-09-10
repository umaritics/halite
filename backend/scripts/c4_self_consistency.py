import os
import sys
from pathlib import Path
import json
import time

backend_dir = str(Path(__file__).resolve().parent.parent)
sys.path.append(backend_dir)

from evaluate_conflict_detection import init_app_state
from services.conflict_engine import classify_conflict

def main():
    graph_repo, groq_service, adapter = init_app_state()
    
    import pandas as pd
    gt_path = Path(backend_dir) / "data/processed/ground_truth_pairs.csv"
    gt_df = pd.read_csv(gt_path)
    
    sample = gt_df.head(30)
    
    results = []
    
    for i, row in sample.iterrows():
        superseding_id = row["superseding_record_id"]
        superseded_id = row["superseded_record_id"]
        
        sr_sup = graph_repo.get_service_record(superseding_id)
        sr_prior = graph_repo.get_service_record(superseded_id)
        
        if not sr_sup or not sr_prior:
            continue
            
        text_new = sr_sup.get("text", "")
        text_old = sr_prior.get("text", "")
        
        labels = []
        latencies = []
        
        for run in range(5):
            t0 = time.time()
            try:
                res = classify_conflict(groq_service, sr_sup, sr_prior)
                labels.append(res.get("classification"))
            except Exception as e:
                labels.append("error")
            latencies.append(time.time() - t0)
            time.sleep(1) # rate limit delay
            
        results.append({
            "record_id": superseding_id,
            "labels": labels,
            "mean_latency": sum(latencies)/len(latencies)
        })
        print(f"Processed {superseding_id}: {labels}")
        
    total_latency = sum(r["mean_latency"] for r in results)
    avg_latency = total_latency / len(results) if results else 0
    
    perfect_agreement = 0
    for r in results:
        if len(set(r["labels"])) == 1 and "error" not in r["labels"]:
            perfect_agreement += 1
            
    print("\n--- Self-Consistency Results ---")
    print(f"Total pairs tested: {len(results)}")
    print(f"Average latency per call: {avg_latency:.2f}s")
    print(f"Perfect agreement (5/5 identical labels): {perfect_agreement} / {len(results)} ({perfect_agreement/len(results):.1%} if len(results) > 0 else 0)")

    md_path = Path(backend_dir) / "docs/c4_results.md"
    with open(md_path, "w") as f:
        f.write("# C4 - Self-Consistency and Latency\n\n")
        f.write(f"- **Total pairs tested (N):** {len(results)}\n")
        f.write(f"- **Average latency per call:** {avg_latency:.2f}s\n")
        f.write(f"- **Perfect agreement (5/5 identical labels):** {perfect_agreement} / {len(results)} ({perfect_agreement/len(results):.1%} if len(results) > 0 else 0)\n")

if __name__ == "__main__":
    main()
