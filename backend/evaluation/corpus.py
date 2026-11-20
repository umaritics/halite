"""Load offline FAA SDR rows for retrieval benchmarks."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

SDR_GLOB = "SDR-*.csv"
_COLUMNS = [
    "OperatorControlNumber",
    "DifficultyDate",
    "SubmissionDate",
    "RegistryNNumber",
    "PartName",
    "JASCCode",
    "Discrepancy",
]


def _parse_submission(raw: str) -> datetime | None:
    text = (raw or "").strip()
    if not text:
        return None
    for fmt in ("%m/%d/%Y", "%m/%d/%Y %H:%M:%S"):
        try:
            return datetime.strptime(text.split("T")[0] if "T" in text else text, fmt).replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            continue
    try:
        return pd.to_datetime(text, utc=True).to_pydatetime()
    except Exception:
        return None


def _normalise_part(name: str) -> str:
    text = (name or "").strip().upper()
    if not text or text == "UNKNOWN":
        return ""
    return text


def load_sdr_raw(raw_dir: Path) -> pd.DataFrame:
    """Load and concatenate SDR-{year}.csv files under ``raw_dir``."""
    paths = sorted(raw_dir.glob(SDR_GLOB))
    if not paths:
        raise FileNotFoundError(f"No {SDR_GLOB} under {raw_dir}")
    frames: list[pd.DataFrame] = []
    for path in paths:
        df = pd.read_csv(path, dtype=str, low_memory=False)
        for col in _COLUMNS:
            if col not in df.columns:
                df[col] = ""
        df = df[_COLUMNS].fillna("")
        df["_source_file"] = path.name
        frames.append(df)
    out = pd.concat(frames, ignore_index=True)
    out = out.drop_duplicates(subset=["OperatorControlNumber"], keep="first")
    out["_submitted_dt"] = out["SubmissionDate"].map(_parse_submission)
    out["_part_norm"] = out["PartName"].map(_normalise_part)
    return out


def record_row_to_graph(row: pd.Series) -> dict:
    return {
        "record_id": row["OperatorControlNumber"],
        "asset_key": row["RegistryNNumber"].strip(),
        "occurred_at": row["DifficultyDate"].strip(),
        "submitted_at": row["SubmissionDate"].strip(),
        "part_name": row["PartName"].strip(),
        "jasc_code": row["JASCCode"].strip(),
        "text": row["Discrepancy"].strip(),
        "status": "auto_accepted",
    }