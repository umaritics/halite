import urllib.request
import json
import urllib.error

def fetch(url, method="GET", data=None):
    try:
        req = urllib.request.Request(url, data=data, method=method, headers={'Content-Type': 'application/json'} if data else {})
        res = urllib.request.urlopen(req)
        body = res.read()
        return json.dumps(json.loads(body), indent=2)
    except urllib.error.HTTPError as e:
        return f"HTTPError {e.code}: {e.read().decode()}"

print("GET /api/health")
print(fetch("http://localhost:8000/api/health"))

print("\nGET /api/domains")
print(fetch("http://localhost:8000/api/domains"))

print("\nPOST /api/maintenance/ingest")
print(fetch("http://localhost:8000/api/maintenance/ingest", method="POST", data=b'{"csv_path":"data/processed/sdr_poc_corpus.csv","limit":300}'))

print("\nGET /api/maintenance/assets")
assets = fetch("http://localhost:8000/api/maintenance/assets")
print("\n".join(assets.split("\n")[:40]))

print("\nGET /api/maintenance/review-queue")
queue = fetch("http://localhost:8000/api/maintenance/review-queue")
print("\n".join(queue.split("\n")[:40]))
