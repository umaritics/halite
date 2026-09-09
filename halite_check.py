#!/usr/bin/env python3
"""
Halite pre-defense diagnostic.

Run this yourself. It does not trust any report — it queries the running
system and prints what is actually true.

Usage:
    # backend running on Neo4j, corpus ingested
    python halite_check.py
    python halite_check.py --base http://localhost:8000
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from collections import Counter

BASE = "http://localhost:8000"
PASS, FAIL, WARN, INFO = "PASS", "FAIL", "WARN", "INFO"
results = []


def log(status, name, detail=""):
    results.append((status, name, detail))
    mark = {PASS: "[PASS]", FAIL: "[FAIL]", WARN: "[WARN]", INFO: "[info]"}[status]
    print(f"{mark} {name}")
    if detail:
        for line in str(detail).splitlines():
            print(f"        {line}")


def get(path, timeout=30):
    url = BASE + path
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def post(path, payload, timeout=120):
    url = BASE + path
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def section(title):
    print("\n" + "=" * 68)
    print(title)
    print("=" * 68)


# ---------------------------------------------------------------- 1. health
def check_health():
    section("1. SYSTEM MODE  — the pre-demo checklist")
    try:
        h = get("/api/health")
    except Exception as e:
        log(FAIL, "/api/health unreachable", f"{e}\nIs the backend running on {BASE}?")
        return None

    gm = str(h.get("graph_mode", "MISSING"))
    lm = str(h.get("llm_mode", "MISSING"))

    log(PASS if gm == "neo4j" else FAIL, f"graph_mode = {gm}",
        "" if gm == "neo4j" else "Demo must run on Neo4j. 'memory' means data vanishes on restart.")
    log(PASS if lm == "live" else FAIL, f"llm_mode = {lm}",
        "" if lm == "live" else "Fallback means canned responses. Any result produced now is worthless.")

    for k in ("domains", "maintenance_record_count", "maintenance_corpus_loaded"):
        log(INFO if k in h else WARN, f"{k} = {h.get(k, 'MISSING')}")

    print("\n  raw /api/health:")
    print("  " + json.dumps(h, indent=2).replace("\n", "\n  "))
    return h


# ------------------------------------------------- 2. the auto-accept problem
def check_record_status():
    section("2. RECORD STATUS + CONFIDENCE  — the reported bug")
    try:
        recs = get("/api/maintenance/records?limit=2000")
    except Exception:
        try:
            recs = get("/api/maintenance/service-records?limit=2000")
        except Exception as e:
            log(WARN, "Could not list records", f"{e}\nCheck the real route name in api/routes/maintenance.py")
            return

    if isinstance(recs, dict):
        recs = recs.get("records") or recs.get("items") or recs.get("data") or []
    if not recs:
        log(FAIL, "No records returned", "Corpus not ingested into this backend.")
        return

    total = len(recs)
    statuses = Counter(str(r.get("status")) for r in recs)
    confs = [r.get("confidence") for r in recs if isinstance(r.get("confidence"), (int, float))]

    log(INFO, f"records inspected: {total}")
    log(INFO, "status distribution", json.dumps(dict(statuses), indent=2))

    auto = statuses.get("auto_accepted", 0)
    review = statuses.get("needs_review", 0)

    if total and auto / total > 0.95:
        log(FAIL, f"{auto}/{total} records are auto_accepted",
            "The confidence gate is not discriminating.\n"
            "Almost certainly bulk ingest never ran process_record and wrote a default status.")
    elif review == 0:
        log(FAIL, "Zero records in needs_review",
            "The Review Queue will be empty. That is the screen the demo depends on.")
    else:
        log(PASS, f"gate is discriminating: {auto} auto / {review} review")

    if confs:
        uniq = set(round(c, 4) for c in confs)
        lo, hi = min(confs), max(confs)
        log(INFO, f"confidence range {lo:.3f} – {hi:.3f}, {len(uniq)} distinct values")
        if len(uniq) == 1:
            log(FAIL, f"every record has confidence {lo}",
                "A single hardcoded value. The engine did not score these records.")
        elif hi <= 0.0 or lo >= 1.0:
            log(FAIL, "confidence is degenerate (all 0 or all 1)")
        else:
            log(PASS, "confidence values vary across records")
    else:
        log(WARN, "No Numeric confidence field found on records")


# ------------------------------------------------------- 3. the review queue
def check_review_queue():
    section("3. REVIEW QUEUE  — most important demo screen")
    try:
        q = get("/api/maintenance/review-queue")
    except Exception as e:
        log(FAIL, "review-queue unreachable", str(e))
        return
    if isinstance(q, dict):
        q = q.get("records") or q.get("items") or q.get("data") or []

    if not q:
        log(FAIL, "Review queue is EMPTY",
            "You cannot demonstrate human-in-the-loop review.\n"
            "Fix: backfill process_record across the ingested corpus so real\n"
            "confidence values are written and low-confidence records route here.")
        return

    log(PASS, f"{len(q)} records awaiting review")
    item = q[0]
    for field in ("candidates_considered", "history_size", "classification", "rationale", "confidence"):
        log(INFO if field in item else WARN, f"queue item field '{field}' = {item.get(field, 'MISSING')}")


# --------------------------------------------------- 4. live single-record run
def check_live_submission():
    section("4. LIVE SUBMISSION  — the pruning line")
    payload = {
        "tail_number": "813SK",
        "date": "12/29/2025",
        "part_name": "DRAG ANGLE",
        "condition": "CRACKED",
        "location": "WING",
        "jasc_code": "5710",
        "discrepancy": "Found crack at drag angle during scheduled inspection. Check history.",
    }
    t0 = time.time()
    try:
        r = post("/api/maintenance/records", payload)
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:400]
        log(FAIL, f"submission failed HTTP {e.code}", body)
        return
    except Exception as e:
        log(FAIL, "submission failed", str(e))
        return
    elapsed = time.time() - t0

    log(PASS if elapsed < 20 else WARN, f"wall clock {elapsed:.1f}s",
        "" if elapsed < 20 else "Too slow for a live demo. Pre-warm the cache.")

    cand = r.get("candidates_considered") or r.get("candidates")
    hist = r.get("history_size") or r.get("history")
    conf = r.get("confidence")
    route = r.get("route") or r.get("status")

    if cand and hist:
        log(PASS, f"pruning: examined {cand} of {hist} records on this asset",
            "THIS is the sentence that justifies the graph. It must also appear in the UI.")
    else:
        log(FAIL, "candidates/history not returned",
            "The pruning line cannot be shown on screen without these fields.")

    log(INFO, f"confidence = {conf}")
    log(INFO, f"route = {route}")
    if conf in (1, 1.0):
        log(FAIL, "live submission also scored 1.00",
            "Confirms the scoring path is bypassed or hardcoded.")
    print("\n  raw response:")
    print("  " + json.dumps(r, indent=2)[:1500].replace("\n", "\n  "))


# ------------------------------------------------------------ 5. diagnostics
def check_diagnostics():
    section("5. DIAGNOSTICS  — ranking + citation integrity")
    try:
        assets = get("/api/maintenance/assets")
    except Exception as e:
        log(FAIL, "assets unreachable", str(e))
        return
    if isinstance(assets, dict):
        assets = assets.get("assets") or assets.get("items") or []
    if not assets:
        log(FAIL, "no assets")
        return

    target = next((a for a in assets if str(a.get("tail_number")) == "813SK"), assets[0])
    aid = target.get("asset_id") or target.get("id")
    log(INFO, f"using asset {target.get('tail_number')} ({aid})")

    t0 = time.time()
    try:
        d = post("/api/maintenance/diagnose",
                 {"asset_id": aid, "symptom_text": "slide light will not extinguish at door 1R"})
    except urllib.error.HTTPError as e:
        log(FAIL, f"diagnose failed HTTP {e.code}", e.read().decode()[:400])
        return
    except Exception as e:
        log(FAIL, "diagnose failed", str(e))
        return
    elapsed = time.time() - t0
    log(PASS if elapsed < 15 else WARN, f"diagnose wall clock {elapsed:.1f}s")

    ranked = d.get("ranked_checks") or []
    ev = d.get("evidence") or []
    log(PASS if ranked else FAIL, f"ranked_checks: {len(ranked)}")
    log(PASS if ev else FAIL, f"evidence items: {len(ev)}")

    ctx = d.get("context_size") or {}
    log(INFO, f"context_size = {json.dumps(ctx)}")
    fleet_assets = ctx.get("fleet_assets") or ctx.get("assets")
    if isinstance(fleet_assets, int) and fleet_assets <= 2:
        log(WARN, f"fleet-wide matching only reached {fleet_assets} assets",
            "Weak evidence base. Retrieval may be over-filtering.")

    # citation integrity — every cited record must exist
    cited = []
    for e in ev:
        rid = e.get("record_id") or e.get("id")
        if rid:
            cited.append(rid)
    txt = json.dumps(d)
    if "[UNVERIFIED" in txt:
        log(FAIL, "response contains [UNVERIFIED:...] markers",
            "The model cited record IDs that do not exist. This is the exact\n"
            "failure the system is supposed to prevent. Do not demo this.")
    else:
        log(PASS, "no UNVERIFIED markers in response")
    log(INFO, f"cited record ids: {len(cited)}", ", ".join(cited[:8]))

    print("\n  first ranked check:")
    print("  " + json.dumps(ranked[0], indent=2).replace("\n", "\n  ") if ranked else "  (none)")


# ----------------------------------------------------------------- 6. chat
def check_chat():
    section("6. CHAT ENDPOINT  — exists but has no UI")
    try:
        r = post("/api/maintenance/chat", {"message": "What is the service history summary?"})
        log(PASS, "chat endpoint responds", json.dumps(r)[:300])
        log(WARN, "No chat UI page was built",
            "Endpoint works; nothing in the frontend calls it. Decide deliberately\n"
            "whether to build the UI or drop the endpoint from the demo narrative.")
    except urllib.error.HTTPError as e:
        log(WARN, f"chat returned HTTP {e.code}", e.read().decode()[:300])
    except Exception as e:
        log(WARN, "chat endpoint not reachable", str(e))


# --------------------------------------------------------------- 7. software
def check_software_regression():
    section("7. SOFTWARE DOMAIN REGRESSION  — must not have broken")
    for path, name in (
        ("/api/decisions", "decisions"),
        ("/api/graph/overview", "graph overview"),
        ("/api/alerts", "alerts"),
    ):
        try:
            r = get(path)
            n = len(r) if isinstance(r, list) else len(r.get("nodes", r.get("items", [])) or [])
            log(PASS, f"{name} responds ({n} items)")
        except Exception as e:
            log(FAIL, f"{name} FAILED", str(e))


def main():
    global BASE
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=BASE)
    args = ap.parse_args()
    BASE = args.base.rstrip("/")

    print(f"Halite pre-defense diagnostic — {BASE}")

    h = check_health()
    check_record_status()
    check_review_queue()
    check_live_submission()
    check_diagnostics()
    check_chat()
    check_software_regression()

    section("SUMMARY")
    counts = Counter(s for s, _, _ in results)
    print(f"  PASS {counts[PASS]}   FAIL {counts[FAIL]}   WARN {counts[WARN]}\n")
    fails = [(n, d) for s, n, d in results if s == FAIL]
    if fails:
        print("  BLOCKERS:")
        for n, d in fails:
            print(f"    - {n}")
        print("\n  Do not present until these are resolved.")
        sys.exit(1)
    print("  No blockers found.")


if __name__ == "__main__":
    main()
