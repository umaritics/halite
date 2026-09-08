"""
G0: Measure misdiagnosis density.

For each ground-truth supersession pair, determine whether the superseding record
names a different component (PartName / JASCCode / PartLocation) than the superseded one.

Decision rule (stated before seeing the numbers):
  ≥ 30% different-part pairs AND ≥ 10 distinct component pairs with support ≥ 3
  → proceed to G2 (mined dependency edges)
  Otherwise → skip G2, build G3 without dependency edges.

Usage:
  python backend/scripts/measure_misdiagnosis_density.py
"""
import csv
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# 1. Load corpus for part metadata lookups
# ---------------------------------------------------------------------------
CORPUS = Path("backend/data/processed/sdr_poc_corpus.csv")
GT_PAIRS = Path("backend/data/processed/ground_truth_pairs.csv")

def normalise(s: str) -> str:
    if not s:
        return ""
    return re.sub(r"\s+", " ", s.strip().upper())

# Build record_id → row lookup from the corpus
record_lookup: dict[str, dict] = {}
with open(CORPUS, newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        rid = row.get("OperatorControlNumber", "").strip()
        if rid:
            record_lookup[rid] = row

print(f"Corpus rows indexed: {len(record_lookup)}")

# ---------------------------------------------------------------------------
# 2. Load ground-truth pairs
# ---------------------------------------------------------------------------
pairs = []
with open(GT_PAIRS, newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        pairs.append(row)

print(f"Ground-truth pairs loaded: {len(pairs)}")

# ---------------------------------------------------------------------------
# 3. For each pair compute part similarity
# ---------------------------------------------------------------------------
results = []
missing = 0

for pair in pairs:
    old_id = pair["superseded_record_id"]
    new_id = pair["superseding_record_id"]

    old_row = record_lookup.get(old_id)
    new_row = record_lookup.get(new_id)

    if old_row is None or new_row is None:
        missing += 1
        continue

    old_part = normalise(old_row.get("PartName", ""))
    new_part = normalise(new_row.get("PartName", ""))
    old_jasc = normalise(old_row.get("JASCCode", ""))
    new_jasc = normalise(new_row.get("JASCCode", ""))
    old_loc  = normalise(old_row.get("PartLocation", ""))
    new_loc  = normalise(new_row.get("PartLocation", ""))

    results.append({
        "old_id":    old_id,
        "new_id":    new_id,
        "old_part":  old_part,
        "new_part":  new_part,
        "old_jasc":  old_jasc,
        "new_jasc":  new_jasc,
        "old_loc":   old_loc,
        "new_loc":   new_loc,
        "diff_part": old_part != new_part,
        "diff_jasc": old_jasc != new_jasc,
        "diff_loc":  old_loc  != new_loc,
    })

N = len(results)
print(f"\nPairs resolved (both records found): {N}")
print(f"Pairs missing from corpus: {missing}")

if N == 0:
    print("No pairs could be resolved. Aborting.")
    sys.exit(1)

# ---------------------------------------------------------------------------
# 4. Aggregate metrics
# ---------------------------------------------------------------------------
n_diff_part = sum(1 for r in results if r["diff_part"])
n_diff_jasc = sum(1 for r in results if r["diff_jasc"])
n_diff_loc  = sum(1 for r in results if r["diff_loc"])

pct_diff_part = 100 * n_diff_part / N
pct_diff_jasc = 100 * n_diff_jasc / N
pct_diff_loc  = 100 * n_diff_loc  / N

print(f"\n--- Part similarity metrics (N={N}) ---")
print(f"  Different PartName:     {n_diff_part}/{N} = {pct_diff_part:.1f}%")
print(f"  Different JASCCode:     {n_diff_jasc}/{N} = {pct_diff_jasc:.1f}%")
print(f"  Different PartLocation: {n_diff_loc}/{N}  = {pct_diff_loc:.1f}%")

# ---------------------------------------------------------------------------
# 5. Top-20 transition pairs (old_part → new_part) where parts differ
# ---------------------------------------------------------------------------
transition_counter: Counter = Counter()
for r in results:
    if r["diff_part"] and r["old_part"] and r["new_part"]:
        transition_counter[(r["old_part"], r["new_part"])] += 1

print(f"\n--- Top-20 (superseded_part -> superseding_part) where PartName differs ---")
top20 = transition_counter.most_common(20)
for i, ((old_p, new_p), cnt) in enumerate(top20, 1):
    print(f"  {i:2d}. {old_p!r:40s} -> {new_p!r:40s}  support={cnt}")

# ---------------------------------------------------------------------------
# 6. Distinct component pairs by support threshold
# ---------------------------------------------------------------------------
support_ge3  = sum(1 for _, cnt in transition_counter.items() if cnt >= 3)
support_ge5  = sum(1 for _, cnt in transition_counter.items() if cnt >= 5)
support_ge10 = sum(1 for _, cnt in transition_counter.items() if cnt >= 10)

print(f"\n--- Distinct component pairs by support ---")
print(f"  support >= 3:  {support_ge3}")
print(f"  support >= 5:  {support_ge5}")
print(f"  support >= 10: {support_ge10}")

# ---------------------------------------------------------------------------
# 7. Decision rule
# ---------------------------------------------------------------------------
threshold_part = 30.0  # %
threshold_pairs_ge3 = 10  # count

g2_go = (pct_diff_part >= threshold_part) and (support_ge3 >= threshold_pairs_ge3)

print(f"\n=== G0 DECISION ===")
print(f"  Threshold: >={threshold_part}% different-part pairs AND >={threshold_pairs_ge3} pairs at support>=3")
print(f"  Observed:  {pct_diff_part:.1f}% different-part pairs, {support_ge3} pairs at support>=3")
if g2_go:
    print("  RESULT: PROCEED TO G2 — mined dependency edges.")
else:
    print("  RESULT: SKIP G2 — build G3 without dependency edges.")

# ---------------------------------------------------------------------------
# 8. Write docs/misdiagnosis_density.md
# ---------------------------------------------------------------------------
OUT = Path("docs/misdiagnosis_density.md")
OUT.parent.mkdir(exist_ok=True)

top20_table = "\n".join(
    f"| {i:2d} | `{old_p}` | `{new_p}` | {cnt} |"
    for i, ((old_p, new_p), cnt) in enumerate(top20, 1)
)

decision_text = (
    "**Proceed to G2** — mined dependency edges are justified by evidence."
    if g2_go else
    "**Skip G2** — both thresholds were not met. G3 is built without dependency edges. "
    "This finding is documented here."
)

md = f"""# G0: Misdiagnosis Density

## Measurement

Ground-truth pairs: **{len(pairs)}** (from `ground_truth_pairs.csv`)
Pairs resolved (both records found in corpus): **{N}**
Pairs missing from corpus: **{missing}**

| Metric | Count | Percentage |
|--------|-------|-----------|
| Different `PartName` | {n_diff_part} | **{pct_diff_part:.1f}%** |
| Different `JASCCode` | {n_diff_jasc} | {pct_diff_jasc:.1f}% |
| Different `PartLocation` | {n_diff_loc} | {pct_diff_loc:.1f}% |

## Top-20 Component Transition Pairs (different PartName only)

| Rank | Superseded Part | Superseding Part | Support |
|------|-----------------|-----------------|---------|
{top20_table}

## Distinct Component Pairs by Support Threshold

| Support ≥ | Distinct Pairs |
|-----------|---------------|
| 3  | {support_ge3} |
| 5  | {support_ge5} |
| 10 | {support_ge10} |

## Decision Rule

**Thresholds**: ≥ 30% different-part pairs AND ≥ 10 distinct component pairs at support ≥ 3.

**Observed**: {pct_diff_part:.1f}% different-part pairs, {support_ge3} pairs at support ≥ 3.

**Decision**: {decision_text}

*The thresholds were stated in the G0 specification before this measurement was run and have not been adjusted.*
"""

OUT.write_text(md, encoding="utf-8")
print(f"\nWrote {OUT}")
