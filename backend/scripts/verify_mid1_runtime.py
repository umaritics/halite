"""Verify the Mid-I maintenance slice against running Docker services.

This script is intentionally deterministic and uses only the synthetic CI fixture.
It never modifies the FAA demo corpus. Run it inside the backend container after
the Compose stack is healthy:

    docker compose exec -T backend python scripts/verify_mid1_runtime.py
"""

from __future__ import annotations

import json
import os
from urllib import error, request

from graph.neo4j_client import Neo4jClient


BASE_URL = os.getenv("MID1_BASE_URL", "http://127.0.0.1:8000")
FIXTURE_PATH = os.getenv(
    "MID1_FIXTURE_PATH", "/app/tests/fixtures/mid1_smoke.csv"
)
RECORD_IDS = ["CI-SMOKE-001", "CI-SMOKE-002", "CI-SMOKE-003"]


def api(method: str, path: str, payload: dict | None = None) -> tuple[int, object]:
    body = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"} if body is not None else {}
    req = request.Request(BASE_URL + path, data=body, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=15) as response:
            raw = response.read().decode()
            return response.status, json.loads(raw) if raw else None
    except error.HTTPError as exc:
        raw = exc.read().decode()
        return exc.code, json.loads(raw) if raw else None


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    proof: dict[str, object] = {}

    status, initial_health = api("GET", "/api/health")
    require(status == 200, f"health returned HTTP {status}")
    require(initial_health["graph_mode"] == "neo4j", initial_health)
    require(initial_health["using_memory_graph"] is False, initial_health)
    require(initial_health["demo_mode"] is False, initial_health)
    proof["initial_health"] = initial_health

    status, first_ingest = api("POST", "/api/maintenance/ingest", {
        "csv_path": FIXTURE_PATH,
    })
    require(status == 200, f"first ingest returned HTTP {status}: {first_ingest}")
    require(first_ingest["records_created"] == 3, first_ingest)
    proof["first_ingest"] = first_ingest

    status, second_ingest = api("POST", "/api/maintenance/ingest", {
        "csv_path": FIXTURE_PATH,
    })
    require(status == 200, f"second ingest returned HTTP {status}: {second_ingest}")
    require(second_ingest["records_created"] == 0, second_ingest)
    require(second_ingest["duplicates_skipped"] == 3, second_ingest)
    proof["idempotent_ingest"] = second_ingest

    status, health = api("GET", "/api/health")
    require(status == 200, f"health after ingest returned HTTP {status}")
    require(health["graph_mode"] == "neo4j", health)
    require(health["maintenance_corpus_loaded"] is True, health)
    require(health["maintenance_record_count"] >= 3, health)
    proof["loaded_health"] = health

    status, assets = api("GET", "/api/maintenance/assets")
    require(status == 200, f"assets returned HTTP {status}")
    asset = next((item for item in assets if item.get("tail_number") == "N-CI-123"), None)
    require(asset is not None, assets)
    require(asset["record_count"] == 3, asset)
    proof["asset"] = asset

    status, history = api(
        "GET", f"/api/maintenance/assets/{asset['id']}/history"
    )
    require(status == 200, f"history returned HTTP {status}")
    require(history["count"] == 3, history)
    require(
        [record["record_id"] for record in history["records"]] == RECORD_IDS,
        history,
    )
    proof["history_record_ids"] = RECORD_IDS

    graph = Neo4jClient(
        os.environ["NEO4J_URI"],
        os.getenv("NEO4J_USERNAME", "neo4j"),
        os.environ["NEO4J_PASSWORD"],
        database=os.getenv("NEO4J_DATABASE", "neo4j"),
    )
    try:
        rows = graph.run_query(
            """
            MATCH (record:ServiceRecord)
            WHERE record.record_id IN $record_ids
            SET record.status = 'needs_review'
            RETURN count(record) AS updated
            """,
            {"record_ids": RECORD_IDS[1:]},
        )
        require(rows[0]["updated"] == 2, rows)
    finally:
        graph.close()

    status, queue = api("GET", "/api/maintenance/review-queue")
    require(status == 200, f"review queue returned HTTP {status}")
    queue_ids = {record["record_id"] for record in queue}
    require(set(RECORD_IDS[1:]).issubset(queue_ids), queue)
    proof["review_queue_ids"] = sorted(queue_ids)

    status, accepted = api(
        "POST",
        "/api/maintenance/review-queue/CI-SMOKE-002/accept",
        {"note": "CI smoke acceptance"},
    )
    require(status == 200 and accepted["status"] == "accepted", accepted)
    require(accepted["record"]["record_id"] == "CI-SMOKE-002", accepted)
    proof["accept_result"] = {
        "record_id": accepted["record_id"],
        "status": accepted["status"],
    }

    status, rejected = api(
        "POST",
        "/api/maintenance/review-queue/CI-SMOKE-003/reject",
        {"note": "CI smoke rejection"},
    )
    require(status == 200 and rejected["status"] == "rejected", rejected)
    require(rejected["record"]["text"].startswith("Pressure sensor"), rejected)
    proof["reject_result"] = {
        "record_id": rejected["record_id"],
        "status": rejected["status"],
        "original_text_preserved": True,
    }

    status, conflict = api("GET", "/api/maintenance/records/CI-SMOKE-001")
    require(status == 503, {"status": status, "body": conflict})
    proof["model_unavailable_failure"] = {
        "status": status,
        "detail": conflict["detail"],
    }

    status, unknown = api(
        "GET", "/api/maintenance/assets/not-a-real-asset/history"
    )
    require(status == 404, {"status": status, "body": unknown})
    proof["unknown_asset_failure"] = {"status": status, "detail": unknown["detail"]}

    print(json.dumps(proof, indent=2, sort_keys=True))
    print("MID1_RUNTIME_SMOKE=PASS")


if __name__ == "__main__":
    main()
