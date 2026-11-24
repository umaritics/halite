import pytest

from integrity.bench.masking import MASKINGS, leaks, mask_text
from integrity.citations import parse_citations

NEW = (
    "FOUND SEAL LEAKING. **SUPPLEMENTAL REPORT FOR (ABCD20240101): REPLACED SEAL PER AMM 29-10-00 "
    "(ABCD20240101) AND CHECKED.** (CLOSED)"
)
OPEN_TEXT = "SEAL LEAKING. ** SUPPLEMENTAL REPORT WILL BE SUBMITTED.** (OPEN)"


@pytest.mark.parametrize("masking", MASKINGS)
def test_citation_and_id_are_removed_everywhere(masking):
    masked = mask_text(NEW, masking, extra_ids=("ABCD20240101",))
    assert "SUPPLEMENTAL REPORT FOR" not in masked.upper()
    assert "ABCD20240101" not in masked
    assert parse_citations(masked) == []
    assert leaks(masked, masking, ("ABCD20240101",)) == []
    assert "REPLACED SEAL PER AMM 29-10-00" in masked


@pytest.mark.parametrize("masking", MASKINGS)
def test_a_prior_that_is_itself_a_supplemental_is_masked_too(masking):
    prior = "SEAL LEAKING. SUPPLEMENTAL REPORT FOR EFGH20230505: SEAL REPLACED"
    assert "EFGH20230505" not in mask_text(prior, masking)


def test_m1_keeps_open_sentence_and_markers_and_m2_removes_them():
    m1 = mask_text(OPEN_TEXT, "M1")
    assert "WILL BE SUBMITTED" in m1 and "(OPEN)" in m1
    assert leaks(m1, "M1") == []
    m2 = mask_text(OPEN_TEXT, "M2")
    assert m2 == "SEAL LEAKING."
    closed = mask_text("DONE ** (closed) .", "M2")
    assert "closed" not in closed.lower()
    assert "( OPEN )" not in mask_text("X ( open ) Y", "M2")


def test_leaks_catches_each_thing_when_it_is_put_back():
    assert leaks("A SUPPLEMENTAL REPORT FOR (ABCD20240101): B", "M1") == ["citation"]
    assert leaks("A SUPPLEMENTAL REPORT WILL BE SUBMITTED", "M2") == ["open_marker"]
    assert leaks("A (OPEN)", "M2") == ["status_marker"]
    assert leaks("A (Closed)", "M2") == ["status_marker"]
    assert leaks("A (OPEN) SUPPLEMENTAL REPORT WILL BE SUBMITTED", "M1") == []
    assert leaks("A ABCD20240101 B", "M1", ("ABCD20240101",)) == ["cited_id"]


def test_a_word_after_for_is_not_a_citation_and_survives():
    text = "SUPPLEMENTAL REPORT FOR ENGINE FAILURE"
    assert mask_text(text, "M1") == text
    assert leaks(text, "M1") == []


def test_whitespace_is_collapsed_and_unknown_masking_raises():
    assert mask_text("  A   B \n C ", "M1") == "A B C"
    with pytest.raises(ValueError):
        mask_text("x", "M3")
    with pytest.raises(ValueError):
        leaks("x", "M3")
