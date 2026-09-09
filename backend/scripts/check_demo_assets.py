"""Check demo assets and corpus content."""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import requests

assets = requests.get("http://localhost:8000/api/maintenance/assets").json()
print(f"Total assets in graph: {len(assets)}")
print()

for tail in ["813SK", "508AE", "860NW"]:
    found = next((a for a in assets if a["tail_number"] == tail), None)
    if found:
        print(f"{tail}: id={found['id']}, records={found['record_count']}")
    else:
        print(f"{tail}: NOT FOUND in graph")

print()

# Check CSV
csv_path = Path("data/processed/sdr_poc_corpus.csv")
if csv_path.exists():
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    print(f"CSV rows: {len(rows)}")
    demo_rows = {r.get("RegistryNNumber", r.get("tail_number", "")) for r in rows}
    for tail in ["813SK", "508AE", "860NW"]:
        cnt = sum(1 for r in rows if r.get("RegistryNNumber", "") == tail or r.get("tail_number", "") == tail)
        print(f"  {tail} in CSV: {cnt} rows")
else:
    print(f"CSV not found at {csv_path}")
