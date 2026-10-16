"""U4 unit tests: FAA-shaped citation extraction + graph verification."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from graph.memory_store import MemoryGraphStore
from graph.queries import GraphRepository
from services.citation_validation import (
    extract_record_id_candidates,
    validate_citations,
)


def _repo_with_faa_ids():
    store = MemoryGraphStore()
    gr = GraphRepository(store)
    asset = gr.find_or_create_asset("N813SK", {})
    for rid, part in [
        ("SWIA2025091876593", "ROLLER"),
        ("AALA202504075792", "PUMP"),
    ]:
        gr.create_service_record({
            "record_id": rid,
            "asset_key": "N813SK",
            "occurred_at": "2025-09-01",
            "part_name": part,
            "text": f"work on {part}",
            "status": "auto_accepted",
        })
        gr.link_record_about_asset(rid, asset["id"])
    return gr


class TestExtractRecordIdCandidates:
    def test_real_faa_shapes(self):
        text = "See SWIA2025091876593 and AALA202504075792 for pump work."
        ids = extract_record_id_candidates(text)
        assert ids == ["SWIA2025091876593", "AALA202504075792"]

    def test_dedupes_preserving_order(self):
        text = "SWIA2025091876593 then again SWIA2025091876593"
        assert extract_record_id_candidates(text) == ["SWIA2025091876593"]

    def test_ignores_short_or_underscore_ids(self):
        text = "SEED001 and R1_OLD are not FAA-shaped; SWIA2025010112345 is."
        assert extract_record_id_candidates(text) == ["SWIA2025010112345"]


class TestValidateCitations:
    def test_all_valid(self):
        gr = _repo_with_faa_ids()
        result = validate_citations(
            "Prior work SWIA2025091876593 and AALA202504075792.",
            gr,
        )
        assert result["valid"] == ["SWIA2025091876593", "AALA202504075792"]
        assert result["invalid"] == []
        assert "[UNVERIFIED:" not in result["flagged_text"]

    def test_invented_id_flagged(self):
        gr = _repo_with_faa_ids()
        result = validate_citations(
            "Invented FAKE2025999999999 vs real SWIA2025091876593.",
            gr,
        )
        assert "SWIA2025091876593" in result["valid"]
        assert "FAKE2025999999999" in result["invalid"]
        assert "[UNVERIFIED:FAKE2025999999999]" in result["flagged_text"]
        assert "SWIA2025091876593" in result["flagged_text"]

    def test_empty_text(self):
        gr = _repo_with_faa_ids()
        result = validate_citations("", gr)
        assert result["valid"] == []
        assert result["invalid"] == []
