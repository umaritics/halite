import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from graph.memory_store import MemoryGraphStore
from graph.queries import GraphRepository
from agents.maintenance_agent import MaintenanceAgent
from pathlib import Path

def main():
    store = MemoryGraphStore()
    repo = GraphRepository(store)
    agent = MaintenanceAgent(repo, None)
    agent.run({"csv_path": "data/processed/sdr_poc_corpus.csv"})
    
    gt_df = pd.read_csv("data/processed/ground_truth_pairs.csv")
    n_gt = 0
    baseline_correct = 0
    
    for _, row in gt_df.iterrows():
        superseding_id = row["superseding_record_id"]
        true_prior_id = row["superseded_record_id"]
        
        sr = repo.get_service_record(superseding_id)
        if not sr:
            continue
            
        n_gt += 1
        asset_id = None
        for e in repo.store.edges:
            if e["source"] == sr["id"] and e["type"] == "ABOUT":
                asset_id = e["target"]
                break
                
        history = repo.list_asset_history(asset_id, limit=200)
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
        
        if baseline_pred_id == true_prior_id:
            baseline_correct += 1
        elif n_gt <= 5:
            print(f"[{n_gt}] Superseding: {superseding_id}")
            print(f"  True Prior: {true_prior_id}")
            print(f"  Baseline  : {baseline_pred_id}")
            print(f"  History length: {len(history)}")
            for x in older[:3]:
                print(f"    - {x['record_id']} ({x['occurred_at']}, {x.get('submitted_at')})")

if __name__ == "__main__":
    main()
