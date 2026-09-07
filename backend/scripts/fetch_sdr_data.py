#!/usr/bin/env python3
"""
fetch_sdr_data.py — FAA SDR data acquisition and profiling script.

Usage:
    python scripts/fetch_sdr_data.py --year 2025 --out data/raw/

Outputs:
    data/raw/SDR-{YEAR}.csv              — raw downloaded file (not committed)
    data/processed/sdr_poc_corpus.csv    — POC corpus (~2000 records, ~60 tails)
    data/processed/ground_truth_pairs.csv — validated supersession pairs
    docs/dataset_profile.md              — human-readable profile
"""
import argparse
import logging
import os
import re
import sys
import urllib.request
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SDR_URL_TEMPLATE = "https://external.apic4e.faa.gov/sdrs/retrieve/SDR-{year}.csv"
MIN_FILE_SIZE_BYTES = 1_000_000  # 1 MB sanity check

# Regex patterns from §5.3
_RE_SUPPLEMENTAL_FOR = re.compile(
    r"SUPPLEMENTAL\s+REPORT\s+FOR\s*\(?\s*([A-Z0-9]{6,})\s*\)?",
    re.IGNORECASE,
)
_RE_OPEN_MARKER = re.compile(
    r"SUPPLEMENTAL\s+REPORT\s+WILL\s+BE\s+SUBMITTED",
    re.IGNORECASE,
)
_RE_IMPLICIT_REF = re.compile(
    r"SEE\s+LONG\s+HISTORY|CHECK\s+HISTORY|HAS\s+HISTORY",
    re.IGNORECASE,
)

# Columns we actually use (§5.2)
_COLS_USED = [
    "OperatorControlNumber",
    "DifficultyDate",
    "SubmissionDate",
    "RegistryNNumber",
    "AircraftMake",
    "AircraftModel",
    "AircraftSerialNumber",
    "PartName",
    "PartCondition",
    "PartLocation",
    "JASCCode",
    "Discrepancy",
]

POC_TARGET_RECORDS = 2000
POC_TARGET_TAILS = 60


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

def download_sdr(year: int, out_dir: Path) -> Path:
    """Download SDR-{year}.csv if not already present and valid."""
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / f"SDR-{year}.csv"

    if dest.exists() and dest.stat().st_size >= MIN_FILE_SIZE_BYTES:
        logger.info("File already present and passes size check: %s", dest)
        return dest

    url = SDR_URL_TEMPLATE.format(year=year)
    logger.info("Downloading %s → %s", url, dest)

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=120) as response:
            total = int(response.headers.get("Content-Length", 0))
            downloaded = 0
            chunk = 65536
            with open(dest, "wb") as f:
                while True:
                    data = response.read(chunk)
                    if not data:
                        break
                    f.write(data)
                    downloaded += len(data)
                    if total:
                        pct = downloaded / total * 100
                        print(f"\r  {pct:5.1f}% ({downloaded:,}/{total:,} bytes)", end="", flush=True)
        print()
        logger.info("Download complete: %s (%d bytes)", dest, dest.stat().st_size)
    except Exception as exc:
        logger.error("Download failed: %s", exc)
        if dest.exists():
            dest.unlink()
        sys.exit(1)

    if dest.stat().st_size < MIN_FILE_SIZE_BYTES:
        logger.error("Downloaded file is suspiciously small (%d bytes). Aborting.", dest.stat().st_size)
        sys.exit(1)

    return dest


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------

def load_csv(path: Path) -> pd.DataFrame:
    """Load CSV with all columns as strings. Returns only columns we use."""
    logger.info("Loading CSV: %s", path)
    df = pd.read_csv(path, dtype=str, low_memory=False)
    logger.info("Raw shape: %s", df.shape)

    # Keep only columns we need (ignore missing columns gracefully)
    cols = [c for c in _COLS_USED if c in df.columns]
    missing = set(_COLS_USED) - set(cols)
    if missing:
        logger.warning("Columns missing from CSV (will treat as blank): %s", missing)
    df = df[cols].copy()

    # Fill missing columns with empty string
    for col in _COLS_USED:
        if col not in df.columns:
            df[col] = ""

    # Strip whitespace from all string fields
    for col in df.columns:
        df[col] = df[col].fillna("").astype(str).str.strip()

    return df


# ---------------------------------------------------------------------------
# Deduplication (§5.4)
# ---------------------------------------------------------------------------

def _normalise_discrepancy(text: str) -> str:
    """Uppercase, collapse whitespace, strip punctuation."""
    text = text.upper()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def deduplicate(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """
    Deduplicate on (RegistryNNumber, DifficultyDate, normalised(Discrepancy)).
    Returns (deduped_df, rows_dropped).
    """
    rows_before = len(df)
    df = df.copy()
    df["_norm_disc"] = df["Discrepancy"].apply(_normalise_discrepancy)
    df = df.drop_duplicates(subset=["RegistryNNumber", "DifficultyDate", "_norm_disc"])
    df = df.drop(columns=["_norm_disc"])
    rows_dropped = rows_before - len(df)
    return df.reset_index(drop=True), rows_dropped


# ---------------------------------------------------------------------------
# Ground-truth extraction (§5.3)
# ---------------------------------------------------------------------------

def extract_ground_truth_pairs(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Extract validated supersession pairs.

    A pair (cited_id, citing_id) is valid only if:
      - cited_id exists in df.OperatorControlNumber
      - both share the same non-empty RegistryNNumber

    Returns:
      pairs_df — valid ground-truth pairs with columns:
                 superseded_record_id, superseding_record_id, tail_number, days_between
      discards  — {reason: count}
    """
    # Build lookup: OperatorControlNumber → row
    ocn_index = df.set_index("OperatorControlNumber").to_dict("index")
    tail_map = df.set_index("OperatorControlNumber")["RegistryNNumber"].to_dict()

    pairs = []
    discards: dict[str, int] = {}

    for _, row in df.iterrows():
        disc = row.get("Discrepancy", "")
        # Find SUPPLEMENTAL REPORT FOR (...) citations
        for m in _RE_SUPPLEMENTAL_FOR.finditer(disc):
            cited_id = m.group(1).strip().upper()

            # Rule 1: cited_id must exist in corpus
            if cited_id not in ocn_index:
                discards["cited_record_not_in_corpus"] = discards.get("cited_record_not_in_corpus", 0) + 1
                continue

            # Rule 2: same non-empty RegistryNNumber
            citing_tail = row.get("RegistryNNumber", "").strip()
            cited_tail = tail_map.get(cited_id, "").strip()
            if not citing_tail:
                discards["citing_record_no_tail"] = discards.get("citing_record_no_tail", 0) + 1
                continue
            if not cited_tail:
                discards["cited_record_no_tail"] = discards.get("cited_record_no_tail", 0) + 1
                continue
            if citing_tail != cited_tail:
                discards["tail_mismatch"] = discards.get("tail_mismatch", 0) + 1
                continue

            # Compute days_between from DifficultyDate
            days_between = None
            try:
                d1 = pd.to_datetime(ocn_index[cited_id]["DifficultyDate"], format="%m/%d/%Y")
                d2 = pd.to_datetime(row["DifficultyDate"], format="%m/%d/%Y")
                days_between = (d2 - d1).days
            except Exception:
                pass

            pairs.append({
                "superseded_record_id": cited_id,
                "superseding_record_id": row["OperatorControlNumber"],
                "tail_number": citing_tail,
                "days_between": days_between,
            })

    pairs_df = pd.DataFrame(pairs) if pairs else pd.DataFrame(
        columns=["superseded_record_id", "superseding_record_id", "tail_number", "days_between"]
    )
    # Drop duplicates (same pair cited multiple times in one record)
    if not pairs_df.empty:
        pairs_df = pairs_df.drop_duplicates(subset=["superseded_record_id", "superseding_record_id"])

    return pairs_df, discards


# ---------------------------------------------------------------------------
# Implicit references (§5.3)
# ---------------------------------------------------------------------------

def find_implicit_references(df: pd.DataFrame) -> int:
    """Count records containing implicit history references."""
    mask = df["Discrepancy"].str.contains(_RE_IMPLICIT_REF, regex=True, na=False)
    return int(mask.sum())


# ---------------------------------------------------------------------------
# POC corpus selection (§5.5)
# ---------------------------------------------------------------------------

def select_poc_corpus(
    df: pd.DataFrame,
    pairs_df: pd.DataFrame,
    target_records: int = POC_TARGET_RECORDS,
    target_tails: int = POC_TARGET_TAILS,
) -> pd.DataFrame:
    """
    Select POC corpus deterministically (fixed seed=42):

    Step 1: All records belonging to tails that appear in ≥1 ground-truth pair.
    Step 2: Top-N additional tails by deduplicated record count until
            ≈target_records across ≈target_tails.
    """
    # Tails with ground-truth pairs
    if not pairs_df.empty and "tail_number" in pairs_df.columns:
        gt_tails = set(pairs_df["tail_number"].dropna().unique())
    else:
        gt_tails = set()

    # Records per tail (deduped df is already deduped)
    tail_counts = (
        df[df["RegistryNNumber"] != ""]
        .groupby("RegistryNNumber")
        .size()
        .sort_values(ascending=False)
        .reset_index(name="count")
    )

    selected_tails: list[str] = list(gt_tails)
    selected = df[df["RegistryNNumber"].isin(gt_tails)].copy()

    # Add top-N tails by record count until we hit targets
    for _, row_t in tail_counts.iterrows():
        tail = row_t["RegistryNNumber"]
        if tail in gt_tails:
            continue
        candidate = df[df["RegistryNNumber"] == tail]
        if len(selected) + len(candidate) > target_records * 1.2:  # 20% headroom
            break
        selected = pd.concat([selected, candidate], ignore_index=True)
        selected_tails.append(tail)
        if len(selected) >= target_records and len(selected_tails) >= target_tails:
            break

    return selected.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Dataset profile
# ---------------------------------------------------------------------------

def compute_profile(
    df_raw: pd.DataFrame,
    df_deduped: pd.DataFrame,
    rows_dropped: int,
    pairs_df: pd.DataFrame,
    discards: dict,
    implicit_count: int,
    corpus_df: pd.DataFrame,
) -> dict:
    """Compute all profile metrics."""
    rows_raw = len(df_raw)
    rows_after_dedupe = len(df_deduped)
    tail_fill = (df_raw["RegistryNNumber"].str.strip() != "").sum() / rows_raw if rows_raw else 0
    dedupe_rate = rows_dropped / rows_raw if rows_raw else 0

    # Records per tail AFTER dedup
    tail_counts = (
        df_deduped[df_deduped["RegistryNNumber"] != ""]
        .groupby("RegistryNNumber")
        .size()
    )
    rpt = tail_counts.describe()

    return {
        "rows_raw": rows_raw,
        "tail_fill_rate_pct": round(tail_fill * 100, 2),
        "rows_after_dedupe": rows_after_dedupe,
        "rows_dropped": rows_dropped,
        "dedupe_rate_pct": round(dedupe_rate * 100, 2),
        "tails_with_records": int((tail_counts > 0).sum()),
        "records_per_tail_count": int(rpt.get("count", 0)),
        "records_per_tail_mean": round(float(rpt.get("mean", 0)), 2),
        "records_per_tail_median": round(float(tail_counts.median()) if len(tail_counts) else 0, 2),
        "records_per_tail_p90": round(float(tail_counts.quantile(0.9)) if len(tail_counts) else 0, 2),
        "records_per_tail_max": int(tail_counts.max()) if len(tail_counts) else 0,
        "tails_ge5": int((tail_counts >= 5).sum()),
        "tails_ge10": int((tail_counts >= 10).sum()),
        "tails_ge20": int((tail_counts >= 20).sum()),
        "ground_truth_pairs": len(pairs_df),
        "discarded_pairs": discards,
        "implicit_reference_count": implicit_count,
        "corpus_records": len(corpus_df),
        "corpus_tails": int((corpus_df["RegistryNNumber"] != "").sum() and corpus_df[corpus_df["RegistryNNumber"] != ""]["RegistryNNumber"].nunique()),
    }


def write_profile_markdown(profile: dict, out_path: Path) -> None:
    lines = [
        "# FAA SDR Dataset Profile",
        "",
        f"Generated by `scripts/fetch_sdr_data.py`.",
        "",
        "## Raw Data",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| rows_raw | {profile['rows_raw']:,} |",
        f"| tail_fill_rate | {profile['tail_fill_rate_pct']}% |",
        "",
        "## Deduplication (§5.4)",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| rows_after_dedupe | {profile['rows_after_dedupe']:,} |",
        f"| rows_dropped | {profile['rows_dropped']:,} |",
        f"| dedupe_rate | {profile['dedupe_rate_pct']}% |",
        "",
        "## Records per Tail (post-dedupe)",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| tails_with_records | {profile['tails_with_records']:,} |",
        f"| mean | {profile['records_per_tail_mean']} |",
        f"| median | {profile['records_per_tail_median']} |",
        f"| p90 | {profile['records_per_tail_p90']} |",
        f"| max | {profile['records_per_tail_max']:,} |",
        f"| tails ≥5 records | {profile['tails_ge5']:,} |",
        f"| tails ≥10 records | {profile['tails_ge10']:,} |",
        f"| tails ≥20 records | {profile['tails_ge20']:,} |",
        "",
        "## Ground Truth Pairs (§5.3)",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| valid_pairs | {profile['ground_truth_pairs']} |",
    ]
    # Decision gate notice
    if profile["ground_truth_pairs"] < 20:
        lines.append("")
        lines.append("> [!WARNING]")
        lines.append(f"> **SMALL SAMPLE**: Only {profile['ground_truth_pairs']} pairs found.")
        lines.append("> Consider fetching SDR-2024.csv and re-running.")
        lines.append("> Evaluation results will be flagged SMALL SAMPLE — indicative only.")

    lines += [
        "",
        "### Discarded Pairs",
        f"| Reason | Count |",
        f"|--------|-------|",
    ]
    for reason, count in (profile["discarded_pairs"] or {}).items():
        lines.append(f"| {reason} | {count} |")
    if not profile["discarded_pairs"]:
        lines.append("| none | 0 |")

    lines += [
        "",
        "## Implicit References",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| records_with_implicit_ref | {profile['implicit_reference_count']} |",
        "",
        "## POC Corpus",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| corpus_records | {profile['corpus_records']:,} |",
        f"| corpus_tails | {profile['corpus_tails']:,} |",
    ]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Profile written: %s", out_path)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Fetch and profile FAA SDR data")
    parser.add_argument("--year", type=int, default=2025, help="SDR year to download")
    parser.add_argument("--out", default="data/raw", help="Output directory for raw CSV")
    args = parser.parse_args()

    raw_dir = Path(args.out)
    processed_dir = Path("data/processed")
    docs_dir = Path("..") / "docs"  # relative to backend/

    # Step 1: Download
    csv_path = download_sdr(args.year, raw_dir)

    # Step 2: Load
    df_raw = load_csv(csv_path)
    rows_raw = len(df_raw)
    logger.info("rows_raw: %d", rows_raw)

    # Step 3: Deduplicate
    df_deduped, rows_dropped = deduplicate(df_raw)
    logger.info("rows_after_dedupe: %d, rows_dropped: %d", len(df_deduped), rows_dropped)

    # Step 4: Ground truth pairs
    logger.info("Extracting ground-truth pairs...")
    pairs_df, discards = extract_ground_truth_pairs(df_deduped)
    logger.info("Ground-truth pairs: %d, discards: %s", len(pairs_df), discards)

    # Step 5: Implicit references
    implicit_count = find_implicit_references(df_deduped)
    logger.info("Implicit reference count: %d", implicit_count)

    # Step 6: POC corpus
    logger.info("Selecting POC corpus...")
    corpus_df = select_poc_corpus(df_deduped, pairs_df)
    logger.info("Corpus: %d records, %d unique tails",
                len(corpus_df),
                corpus_df[corpus_df["RegistryNNumber"] != ""]["RegistryNNumber"].nunique())

    # Step 7: Write outputs
    processed_dir.mkdir(parents=True, exist_ok=True)
    corpus_path = processed_dir / "sdr_poc_corpus.csv"
    pairs_path = processed_dir / "ground_truth_pairs.csv"
    corpus_df.to_csv(corpus_path, index=False)
    pairs_df.to_csv(pairs_path, index=False)
    logger.info("Corpus written: %s", corpus_path)
    logger.info("Ground truth pairs written: %s", pairs_path)

    # Step 8: Profile
    profile = compute_profile(df_raw, df_deduped, rows_dropped, pairs_df, discards, implicit_count, corpus_df)
    write_profile_markdown(profile, docs_dir / "dataset_profile.md")

    # Step 9: Print summary
    print("\n" + "=" * 60)
    print("DATASET PROFILE SUMMARY")
    print("=" * 60)
    print(f"  rows_raw:              {profile['rows_raw']:,}")
    print(f"  tail_fill_rate:        {profile['tail_fill_rate_pct']}%")
    print(f"  rows_after_dedupe:     {profile['rows_after_dedupe']:,}")
    print(f"  rows_dropped:          {profile['rows_dropped']:,} ({profile['dedupe_rate_pct']}%)")
    print(f"  tails_with_records:    {profile['tails_with_records']:,}")
    print(f"  records/tail mean:     {profile['records_per_tail_mean']}")
    print(f"  records/tail median:   {profile['records_per_tail_median']}")
    print(f"  records/tail p90:      {profile['records_per_tail_p90']}")
    print(f"  records/tail max:      {profile['records_per_tail_max']}")
    print(f"  tails >=5:             {profile['tails_ge5']:,}")
    print(f"  tails >=10:            {profile['tails_ge10']:,}")
    print(f"  tails >=20:            {profile['tails_ge20']:,}")
    print(f"  ground_truth_pairs:    {profile['ground_truth_pairs']}")
    print(f"  implicit_refs:         {profile['implicit_reference_count']}")
    print(f"  corpus_records:        {profile['corpus_records']:,}")
    print(f"  corpus_tails:          {profile['corpus_tails']:,}")
    print("=" * 60)

    # Decision gate (§T3)
    if profile["ground_truth_pairs"] < 20:
        print(f"\nDECISION GATE: Only {profile['ground_truth_pairs']} ground-truth pairs.")
        print("   Evaluation set is small. Consider also fetching SDR-2024.csv.")
        print("   Do NOT invent pairs or relax SS5.3 validity rules.")
    else:
        print(f"\n[PASS] Ground-truth pairs: {profile['ground_truth_pairs']} (>=20 threshold met)")

    print(f"\nOutputs:")
    print(f"  {corpus_path}")
    print(f"  {pairs_path}")
    print(f"  {docs_dir / 'dataset_profile.md'}")


if __name__ == "__main__":
    main()
