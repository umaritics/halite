"""Gather G-1 evidence: API responses for the G-1 evidence checklist."""
import json
import requests

BASE = "http://localhost:8000"

# --- G-1.1: assets ---
assets_r = requests.get(f"{BASE}/api/maintenance/assets")
assets = assets_r.json()
print(f"=== G-1.1: /api/maintenance/assets ===")
print(f"Total assets: {len(assets)}")
print("First 10 tail numbers:")
for a in assets[:10]:
    print(f"  {a['tail_number']}  records={a['record_count']}")

# 813SK id
sk = next(a for a in assets if a["tail_number"] == "813SK")
sk_id = sk["id"]
print(f"\n813SK id: {sk_id}, record_count: {sk['record_count']}")

# --- G-1.2: 813SK history ---
print(f"\n=== G-1.2: /api/maintenance/assets/{sk_id}/history ===")
hist_r = requests.get(f"{BASE}/api/maintenance/assets/{sk_id}/history")
hist = hist_r.json()
print(f"records count in response: {hist['count']}")
print(f"First record: record_id={hist['records'][0]['record_id']}, occurred_at={hist['records'][0]['occurred_at']}, status={hist['records'][0]['status']}")
print(f"Last record:  record_id={hist['records'][-1]['record_id']}, occurred_at={hist['records'][-1]['occurred_at']}, status={hist['records'][-1]['status']}")

# --- G-1.3: process record SWIA2025122876590 ---
target_id = "SWIA2025122876590"
print(f"\n=== G-1.3: POST /api/maintenance/records (record_id={target_id}) ===")
proc_r = requests.post(f"{BASE}/api/maintenance/records", json={"record_id": target_id})
if proc_r.status_code == 200:
    proc = proc_r.json()
    print(f"candidates_considered: {proc['candidates_considered']}")
    print(f"confidence: {proc['confidence']}")
    print(f"route: {proc['route']}")
    print(f"status_applied: {proc['status_applied']}")
    print(f"best_prior: {proc.get('best_prior', {}).get('record_id') if proc.get('best_prior') else None}")
    print(f"classification label: {proc.get('classification', {}).get('label') if proc.get('classification') else None}")
    pruning_line = f"Examined {proc['candidates_considered']} of {sk['record_count']} records on this asset."
    print(f"\nExpected pruning line: \"{pruning_line}\"")
else:
    print(f"ERROR {proc_r.status_code}: {proc_r.text}")

# --- G-1.4: /api/health ---
print(f"\n=== G-1.4: /api/health ===")
health_r = requests.get(f"{BASE}/api/health")
health = health_r.json()
print(json.dumps(health, indent=2))

# --- G-1.6: PR #1 ---
print(f"\n=== G-1.6: PR #1 ===")
print("URL: https://github.com/umaritics/halite/pull/1")
print("(Check GitHub directly for title, branch pair and file count)")
