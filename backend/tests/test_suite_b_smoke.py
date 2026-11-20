"""Smoke tests for offline Suite B harness."""
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from evaluation.suite_b import SuiteBConfig, run_suite_b


@pytest.fixture()
def mini_corpus(tmp_path: Path) -> Path:
    raw = tmp_path / "raw"
    raw.mkdir()
    rows = [
        {
            "OperatorControlNumber": "OLD1",
            "DifficultyDate": "01/01/2025",
            "SubmissionDate": "01/02/2025",
            "RegistryNNumber": "NTST1",
            "PartName": "UNKNOWN",
            "JASCCode": "2900",
            "Discrepancy": "Hydraulic pump noise on ground check",
        },
        {
            "OperatorControlNumber": "NEW1",
            "DifficultyDate": "01/01/2025",
            "SubmissionDate": "01/05/2025",
            "RegistryNNumber": "NTST1",
            "PartName": "PUMP",
            "JASCCode": "2900",
            "Discrepancy": "SUPPLEMENTAL REPORT FOR OLD1 pump found cracked",
        },
        {
            "OperatorControlNumber": "FLEET1",
            "DifficultyDate": "12/01/2024",
            "SubmissionDate": "12/15/2024",
            "RegistryNNumber": "NOTHER",
            "PartName": "PUMP",
            "JASCCode": "2900",
            "Discrepancy": "Hydraulic pump cracked during inspection",
        },
    ]
    pd.DataFrame(rows).to_csv(raw / "SDR-2025.csv", index=False)
    pairs = pd.DataFrame(
        [
            {
                "superseded_record_id": "OLD1",
                "superseding_record_id": "NEW1",
                "tail_number": "NTST1",
                "source_year": "2025",
                "superseding_part": "PUMP",
            }
        ]
    )
    pairs.to_csv(tmp_path / "pairs.csv", index=False)
    (tmp_path / "splits.json").write_text(
        json.dumps({"test_years": [2025]}),
        encoding="utf-8",
    )
    return tmp_path


def test_suite_b_b1_top1_on_mini_corpus(mini_corpus: Path):
    cfg = SuiteBConfig(
        raw_dir=mini_corpus / "raw",
        pairs_path=mini_corpus / "pairs.csv",
        splits_path=mini_corpus / "splits.json",
        split="test",
    )
    result = run_suite_b(cfg, ranker="b1")
    assert result["pairs_evaluated"] == 1
    assert result["top1_accuracy"] == 1.0