import time
import requests

# 1. Ingest corpus
print("Ingesting corpus...")
r_ingest = requests.post('http://localhost:8000/api/maintenance/ingest', json={"csv_path": "data/processed/sdr_poc_corpus.csv", "limit": 100})
print("Ingest:", r_ingest.status_code)

# 2. Pick a known record that has priors (e.g. AALA202504283187 from earlier logs)
# Actually, if we just ingested limit=100, we can pick the last one.
# Let's get list of assets and their history
r_assets = requests.get('http://localhost:8000/api/maintenance/assets').json()
if not r_assets:
    print("No assets found")
    exit(1)

import pandas as pd
from pathlib import Path

# Ingest corpus
print("Ingesting corpus...")
r_ingest = requests.post('http://localhost:8000/api/maintenance/ingest', json={"csv_path": "data/processed/sdr_poc_corpus.csv", "limit": 1000})
print("Ingest:", r_ingest.status_code)

gt_path = Path("data/processed/ground_truth_pairs.csv")
gt_df = pd.read_csv(gt_path)

# pick first valid pair
chosen_record_id = gt_df.iloc[0]["superseding_record_id"]

print(f"Testing on record_id: {chosen_record_id}")

latencies = []
for i in range(5):
    t = time.time()
    r = requests.post('http://localhost:8000/api/maintenance/records', json={
        "record_id": chosen_record_id
    })
    elapsed = time.time() - t
    latencies.append(elapsed)
    print(f"Run {i+1} wall clock seconds: {round(elapsed, 2)}")
    print(r.json())
    time.sleep(1) # ratelimit padding

latencies.sort()
print(f"Min: {latencies[0]:.2f}s, Median: {latencies[2]:.2f}s, Max: {latencies[4]:.2f}s")

