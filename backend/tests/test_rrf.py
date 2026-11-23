import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from evaluation.rrf import reciprocal_rank_fusion


def test_rrf_promotes_consensus_part():
    a = [{"part_name": "ALPHA", "rank": 1, "evidence_record_ids": ["1"], "sources": ["a"]}]
    b = [{"part_name": "BETA", "rank": 1, "evidence_record_ids": ["2"], "sources": ["b"]}]
    b2 = [{"part_name": "ALPHA", "rank": 2, "evidence_record_ids": ["3"], "sources": ["b"]}]
    merged = reciprocal_rank_fusion([a, b, b2], k=60)
    assert merged[0]["part_name"] == "ALPHA"