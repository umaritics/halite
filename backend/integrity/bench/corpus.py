"""FAA yearly files as the record dicts the app stores, plus the citation chains between them.

The benchmark must see the same fields staging sees, so the column mapping mirrors
agents/maintenance_agent.py and the rows the ingest would skip are skipped and counted here.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
from datetime import datetime

from integrity.citations import parse_citations

# Mirrors CONTRACTS.md section 4.4 (splits.json).
SPLITS = {"fit": [2023], "select": [2024], "test": [2025]}

_FIELDS = {
    "record_id": "OperatorControlNumber",
    "asset_key": "RegistryNNumber",
    "submitted_at": "SubmissionDate",
    "part_name": "PartName",
    "part_condition": "PartCondition",
    "part_location": "PartLocation",
    "jasc_code": "JASCCode",
    "text": "Discrepancy",
    "stage_of_operation": "StageOfOperationCode",
    "how_discovered": "HowDiscoveredCode",
    "nature_of_condition": "NatureOfConditionA",
    "precautionary_procedure": "PrecautionaryProcedureA",
}
_REQUIRED_COLUMNS = (*_FIELDS.values(), "DifficultyDate")


def split_of(year: int) -> str:
    """Name the split a year belongs to; an unknown year is an error, not a silent default."""
    for name, years in SPLITS.items():
        if year in years:
            return name
    raise ValueError(f"year {year} is not in SPLITS {SPLITS}")


def file_sha256(path) -> str:
    """Fingerprint of a source file, so a result can name the exact data it came from."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _open_text(path):
    path = str(path)
    if path.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8-sig", newline="")
    return open(path, encoding="utf-8-sig", newline="")


def _iso_date(raw: str) -> str | None:
    try:
        return datetime.strptime((raw or "").strip(), "%m/%d/%Y").strftime("%Y-%m-%d")
    except ValueError:
        return None


def load_year(path, year: int) -> tuple[list[dict], dict]:
    """Read one FAA yearly file into record dicts and say how many rows were skipped and why."""
    csv.field_size_limit(2**31 - 1)
    stats = {
        "rows_read": 0,
        "records": 0,
        "skipped_no_record_id": 0,
        "skipped_no_tail": 0,
        "skipped_bad_date": 0,
        "skipped_duplicate_id": 0,
    }
    records: list[dict] = []
    seen: set[str] = set()
    with _open_text(path) as handle:
        reader = csv.DictReader(handle)
        missing = [c for c in _REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{path}: missing required column(s): {', '.join(missing)}")
        for raw in reader:
            stats["rows_read"] += 1
            fields = {key: (raw.get(col) or "").strip() for key, col in _FIELDS.items()}
            if not fields["asset_key"]:
                stats["skipped_no_tail"] += 1
                continue
            occurred_at = _iso_date(raw.get("DifficultyDate"))
            if occurred_at is None:
                stats["skipped_bad_date"] += 1
                continue
            if not fields["record_id"]:
                stats["skipped_no_record_id"] += 1
                continue
            if fields["record_id"] in seen:
                stats["skipped_duplicate_id"] += 1
                continue
            seen.add(fields["record_id"])
            records.append({**fields, "occurred_at": occurred_at, "year": year})
    stats["records"] = len(records)
    return records, stats


class Corpus:
    """All loaded reports, indexed by id and by aircraft, with their citation chains."""

    def __init__(self, records: list[dict]):
        self.by_id = {r["record_id"]: r for r in records}
        self._by_tail: dict[str, list[dict]] = {}
        for record in sorted(self.by_id.values(), key=lambda r: (r["occurred_at"], r["record_id"])):
            self._by_tail.setdefault(record["asset_key"], []).append(record)
        self._chain: dict[str, frozenset[str]] = {}
        self._link_chains()

    def history(self, tail: str) -> list[dict]:
        """Every report of the aircraft, oldest occurrence first (the order staging reads)."""
        return self._by_tail.get(tail, [])

    def chain_of(self, record_id: str) -> frozenset[str]:
        """Reports joined to this one by 'new cites old' links on the same aircraft, itself included."""
        return self._chain.get(record_id, frozenset({record_id}))

    def _link_chains(self) -> None:
        """Connected components, so siblings that correct the same original share a chain."""
        parent = {rid: rid for rid in self.by_id}

        def find(rid: str) -> str:
            while parent[rid] != rid:
                parent[rid] = parent[parent[rid]]
                rid = parent[rid]
            return rid

        for record in self.by_id.values():
            for cited in parse_citations(record["text"]):
                other = self.by_id.get(cited)
                if other is not None and cited != record["record_id"] and other["asset_key"] == record["asset_key"]:
                    parent[find(record["record_id"])] = find(cited)
        members: dict[str, set[str]] = {}
        for rid in self.by_id:
            members.setdefault(find(rid), set()).add(rid)
        for group in members.values():
            frozen = frozenset(group)
            for rid in group:
                self._chain[rid] = frozen
