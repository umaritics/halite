import csv
import gzip
import json

import pytest

from integrity.bench import build as bench_build
from integrity.bench.build import SplitLockedError, build, main
from integrity.bench.corpus import SPLITS, Corpus, file_sha256, load_year, split_of
from integrity.timeutil import parse_submitted

COLUMNS = [
    "OperatorControlNumber", "DifficultyDate", "SubmissionDate", "RegistryNNumber", "PartName",
    "PartCondition", "PartLocation", "JASCCode", "Discrepancy", "StageOfOperationCode",
    "HowDiscoveredCode", "NatureOfConditionA", "PrecautionaryProcedureA", "AircraftMake",
]


def faa(rid, tail, submitted, text, part="SEAL", jasc="2910", loc="LEFT", occurred="01/05/2024"):
    return {
        "OperatorControlNumber": rid, "DifficultyDate": occurred, "SubmissionDate": submitted,
        "RegistryNNumber": tail, "PartName": part, "PartCondition": "LEAKING", "PartLocation": loc,
        "JASCCode": jasc, "Discrepancy": text, "StageOfOperationCode": "4", "HowDiscoveredCode": "A",
        "NatureOfConditionA": "7", "PrecautionaryProcedureA": "9", "AircraftMake": "X",
    }


def write_year(directory, year, rows, columns=COLUMNS, name=None):
    path = directory / (name or f"SDR-{year}.csv")
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "wt", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path


def at(day, hour=10):
    return f"2024-{day}T{hour:02d}:00:00.000-05:00"


# One tail per scenario; ids are six or more letters and digits so they parse as citations.
CHAIN = [  # A <- B <- C
    faa("AAAA000001", "N1", at("01-01"), "SEAL LEAK ON PUMP **SUPPLEMENTAL REPORT WILL BE SUBMITTED** (OPEN)"),
    faa("AAAA000002", "N1", at("01-05"), "SEAL LEAK ON PUMP. SUPPLEMENTAL REPORT FOR (AAAA000001): REPLACED SEAL (CLOSED)"),
    faa("AAAA000003", "N1", at("01-10"), "SEAL LEAK ON PUMP REPLACED SEAL. SUPPLEMENTAL REPORT FOR AAAA000002: TORQUE CHECKED"),
]
SIBLINGS = [  # D <- E and D <- F, with U an unrelated report on the same aircraft
    faa("UUUU000009", "N2", at("01-01", 8), "CABIN LIGHT FLICKERS IN ROW 4"),
    faa("DDDD000001", "N2", at("01-02"), "SEAL LEAK ON PUMP"),
    faa("DDDD000002", "N2", at("01-04"),
        "SEAL LEAK ON PUMP. SUPPLEMENTAL REPORT FOR (DDDD000001): REPLACED SEAL WITH NEW PART AND TESTED"),
    faa("DDDD000003", "N2", at("01-08"),
        "SEAL REPLACED WITH NEW PART AND TESTED TORQUE CHECKED. SUPPLEMENTAL REPORT FOR (DDDD000001): DONE"),
]
SAME_MOMENT = [
    faa("HHHH000001", "N3", at("02-01"), "SEAL LEAK ON PUMP"),
    faa("HHHH000002", "N3", at("02-01"), "SEAL LEAK ON PUMP. SUPPLEMENTAL REPORT FOR HHHH000001: FIXED"),
]
NO_SHARED_SIGNAL = [
    faa("JJJJ000001", "N4", at("01-02"), "DOOR STUCK", part="DOOR", jasc="5200", loc="AFT", occurred="01/01/2024"),
    faa("KKKK000001", "N4", at("06-02"), "SUPPLEMENTAL REPORT FOR JJJJ000001: DOOR FIXED",
        part="HINGE", jasc="5300", loc="FWD", occurred="06/01/2024"),
]
BAD_CITATIONS = [
    faa("RRRR000001", "N5", at("03-01"), "SUPPLEMENTAL REPORT FOR (RRRR000001): ITSELF"),
    faa("RRRR000002", "N5", at("03-02"), "SUPPLEMENTAL REPORT FOR ZZZZ999999: ABSENT"),
    faa("RRRR000003", "N5", at("03-03"), "SUPPLEMENTAL REPORT FOR AAAA000001: OTHER AIRCRAFT"),
]
MANY = [faa(f"MMMM{n:06d}", "N7", f"2024-04-{n:02d}T09:00:00.000-05:00", f"PUMP SEAL NOTE {n} UNIQUE{n}")
        for n in range(1, 29)]
MAIN_ROWS = CHAIN + SIBLINGS + SAME_MOMENT + NO_SHARED_SIGNAL + BAD_CITATIONS + MANY


@pytest.fixture
def raw(tmp_path):
    directory = tmp_path / "raw"
    directory.mkdir()
    write_year(directory, 2024, MAIN_ROWS)
    return directory


def run(raw, tmp_path, masking="M1", name="out", **options):
    out = tmp_path / name
    manifest = build(raw, 2024, masking, out, **options)
    rows = [json.loads(line) for line in (out / f"bench_2024_{masking}.jsonl").read_text().splitlines()]
    return manifest, rows, out


def by_pair(rows):
    return {r["pair_id"]: r for r in rows}


# ---- corpus ---------------------------------------------------------------------------------

def test_load_year_maps_columns_like_the_ingest_and_counts_skips(tmp_path):
    rows = [
        faa("OKOK000001", " N1 ", at("01-01"), "  text  "),
        faa("OKOK000001", "N1", at("01-02"), "duplicate id"),
        faa("", "N1", at("01-03"), "no id"),
        faa("NOTAIL0001", "", at("01-03"), "no tail"),
        faa("BADDATE001", "N1", at("01-03"), "bad date", occurred="13/45/2024"),
    ]
    path = write_year(tmp_path, 2024, rows, name="SDR-2024.csv.gz")
    records, stats = load_year(path, 2024)
    assert len(records) == 1
    assert records[0] == {
        "record_id": "OKOK000001", "asset_key": "N1", "occurred_at": "2024-01-05", "submitted_at": at("01-01"),
        "part_name": "SEAL", "part_condition": "LEAKING", "part_location": "LEFT", "jasc_code": "2910",
        "text": "text", "stage_of_operation": "4", "how_discovered": "A", "nature_of_condition": "7",
        "precautionary_procedure": "9", "year": 2024,
    }
    assert stats == {
        "rows_read": 5, "records": 1, "skipped_no_record_id": 1, "skipped_no_tail": 1,
        "skipped_bad_date": 1, "skipped_duplicate_id": 1,
    }
    assert len(file_sha256(path)) == 64


def test_a_missing_column_raises_and_names_it(tmp_path):
    path = write_year(tmp_path, 2024, [], columns=[c for c in COLUMNS if c != "PartName"])
    with pytest.raises(ValueError, match="PartName"):
        load_year(path, 2024)


def test_splits_mirror_the_contract():
    assert SPLITS == {"fit": [2023], "select": [2024], "test": [2025]}
    assert [split_of(y) for y in (2023, 2024, 2025)] == ["fit", "select", "test"]
    with pytest.raises(ValueError):
        split_of(2019)


def test_chain_of_follows_citations_between_same_aircraft_reports(tmp_path):
    path = write_year(tmp_path, 2024, MAIN_ROWS)
    corpus = Corpus(load_year(path, 2024)[0])
    assert corpus.chain_of("AAAA000002") == {"AAAA000001", "AAAA000002", "AAAA000003"}
    assert corpus.chain_of("DDDD000002") == {"DDDD000001", "DDDD000002", "DDDD000003"}
    assert corpus.chain_of("UUUU000009") == {"UUUU000009"}
    # Citing another aircraft's report, or itself, or a missing one, joins nothing.
    assert corpus.chain_of("RRRR000003") == {"RRRR000003"}
    assert corpus.chain_of("RRRR000001") == {"RRRR000001"}
    assert [r["record_id"] for r in corpus.history("N2")][0] == "DDDD000001"  # oldest occurrence, then id


# ---- masking in the built files --------------------------------------------------------------

@pytest.mark.parametrize("masking", ["M1", "M2"])
def test_no_citation_reaches_either_text_and_m2_also_drops_status(raw, tmp_path, masking):
    _, rows, _ = run(raw, tmp_path, masking)
    for row in rows:
        for side in ("new", "prior"):
            text = row[side]["text"].upper()
            assert "SUPPLEMENTAL REPORT FOR" not in text
            if masking == "M2":
                assert "(OPEN)" not in text and "(CLOSED)" not in text and "WILL BE SUBMITTED" not in text
    pair = by_pair(rows)["AAAA000002|AAAA000001"]
    assert "AAAA000001" not in pair["new"]["text"]
    assert ("(OPEN)" in pair["prior"]["text"]) == (masking == "M1")
    assert ("(CLOSED)" in pair["new"]["text"]) == (masking == "M1")


def test_a_leak_stops_the_build(raw, tmp_path, monkeypatch):
    monkeypatch.setattr(bench_build, "mask_text", lambda text, masking, extra_ids=(): text)
    with pytest.raises(ValueError, match="leaks"):
        run(raw, tmp_path)


# ---- positives, chains and ranks -------------------------------------------------------------

def test_positives_are_the_valid_citations_and_bad_ones_are_counted(raw, tmp_path):
    manifest, rows, _ = run(raw, tmp_path)
    positives = {r["pair_id"] for r in rows if r["kind"] == "positive"}
    assert positives == {
        "AAAA000002|AAAA000001", "AAAA000003|AAAA000002", "DDDD000002|DDDD000001",
        "DDDD000003|DDDD000001", "HHHH000002|HHHH000001", "KKKK000001|JJJJ000001",
    }
    assert manifest["citations_found"] == 9
    assert manifest["rejected_citations"] == {
        "cites_itself": 1, "cited_id_absent": 1, "other_aircraft": 1, "prior_submitted_later": 0,
    }
    assert manifest["counts"]["positive"] == 6
    assert manifest["counts"]["presumed_negative"] == 6  # default: as many as positives
    assert manifest["split"] == "select" and manifest["unlock_test_reason"] is None
    assert [s["file"] for s in manifest["sources"]] == ["SDR-2024.csv"]


def test_chain_members_are_never_hard_negatives_and_chain_ranks_differ(raw, tmp_path):
    _, rows, _ = run(raw, tmp_path)
    pairs = by_pair(rows)
    path = write_year(tmp_path, "chk", MAIN_ROWS)
    corpus = Corpus(load_year(path, 2024)[0])
    hard = [r for r in rows if r["kind"] == "hard_negative"]
    assert hard
    for row in hard:
        assert row["label"] == 0
        assert row["prior"]["record_id"] not in corpus.chain_of(row["new"]["record_id"])
    assert {r["pair_id"] for r in hard if r["new"]["record_id"] == "DDDD000002"} == {"DDDD000002|UUUU000009"}
    # F cites D, but its sibling E is the stricter first answer; ignoring the chain, D is first.
    sibling = pairs["DDDD000003|DDDD000001"]
    assert sibling["ranks"]["containment"] == 2
    assert sibling["ranks_ignoring_chain"]["containment"] == 1
    # E has no sibling submitted before it, so nothing changes.
    first = pairs["DDDD000002|DDDD000001"]
    assert first["ranks"] == first["ranks_ignoring_chain"]
    assert set(first["ranks"]) == {"legacy", "containment", "submission_gap"}


def test_why_a_true_prior_is_not_a_candidate(raw, tmp_path):
    _, rows, _ = run(raw, tmp_path)
    pairs = by_pair(rows)
    same_moment = pairs["HHHH000002|HHHH000001"]
    assert same_moment["ranks"] == {"legacy": None, "containment": None, "submission_gap": None}
    assert same_moment["not_candidate_reason"] == "not_strictly_earlier"
    no_signal = pairs["KKKK000001|JJJJ000001"]
    assert no_signal["not_candidate_reason"] == "score_zero"
    assert no_signal["pair_score"] == 0
    found = pairs["AAAA000002|AAAA000001"]
    assert found["not_candidate_reason"] is None and found["pair_score"] > 0 and found["n_candidates"] == 1
    assert found["submission_gap_days"] == pytest.approx(4.0)


def test_no_candidate_is_submitted_at_or_after_the_new_report(raw, tmp_path):
    _, rows, _ = run(raw, tmp_path, negatives=20)
    for row in rows:
        gap = row["submission_gap_days"]
        assert parse_submitted(row["new"]["submitted_at"]) is not None
        if row["kind"] == "positive":
            assert gap >= 0  # an announced pair may share a clock tick, never run backwards
        else:
            assert gap > 0, row["pair_id"]


def test_presumed_negatives_have_no_citation_and_use_the_top_containment_candidate(raw, tmp_path):
    _, rows, _ = run(raw, tmp_path, negatives=10)
    presumed = [r for r in rows if r["kind"] == "presumed_negative"]
    assert len(presumed) == 10
    cited_or_citing = {"AAAA000001", "AAAA000002", "AAAA000003", "DDDD000001", "DDDD000002", "DDDD000003",
                       "HHHH000001", "HHHH000002", "JJJJ000001", "KKKK000001"}
    for row in presumed:
        assert row["new"]["record_id"] not in cited_or_citing
        assert row["prior"]["record_id"] not in cited_or_citing
        assert row["rank"] == 1 and row["label"] == 0 and row["n_candidates"] >= 1


# ---- the history cap ---------------------------------------------------------------------------

def test_the_history_cap_hides_a_true_prior_and_ranks_capped_shows_it(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    older = [
        faa(f"OLDR{n:06d}", "N6", f"2023-0{n}-02T10:00:00.000-05:00", f"PUMP SEAL OLD {n}", occurred=f"0{n}/01/2023")
        for n in range(1, 6)
    ]
    write_year(raw, 2023, older)
    write_year(raw, 2024, [faa("NEWW000001", "N6", at("02-01"), "SUPPLEMENTAL REPORT FOR OLDR000005: FIXED",
                               occurred="05/09/2023")])
    uncapped_manifest, uncapped, _ = run(raw, tmp_path, history_limit=0, name="a")
    capped_manifest, capped, _ = run(raw, tmp_path, history_limit=3, name="b")
    assert [s["file"] for s in capped_manifest["sources"]] == ["SDR-2023.csv", "SDR-2024.csv"]
    assert uncapped[0]["ranks"]["legacy"] is not None
    assert uncapped[0]["ranks_capped"] == uncapped[0]["ranks"]
    assert uncapped_manifest["positives_hidden_by_history_cap"] == 0
    assert capped[0]["ranks"]["legacy"] is not None  # the uncapped ranks are kept
    assert capped[0]["ranks_capped"] == {"legacy": None, "containment": None, "submission_gap": None}
    assert capped_manifest["positives_hidden_by_history_cap"] == 1
    assert capped_manifest["options"]["history_limit"] == 3


# ---- the held-out year ---------------------------------------------------------------------------

def test_building_the_test_split_is_refused_without_a_reason_and_records_one_with_it(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    write_year(raw, 2025, [faa("TTTT000001", "N9", "2025-01-01T10:00:00.000-05:00", "PUMP SEAL", occurred="01/01/2025"),
                           faa("TTTT000002", "N9", "2025-01-09T10:00:00.000-05:00",
                               "SUPPLEMENTAL REPORT FOR TTTT000001: FIXED", occurred="01/01/2025")])
    out = tmp_path / "out"
    with pytest.raises(SplitLockedError):
        build(raw, 2025, "M2", out)
    with pytest.raises(SplitLockedError):
        build(raw, 2025, "M2", out, unlock_test="   ")
    assert not out.exists()
    argv = ["--raw-dir", str(raw), "--year", "2025", "--masking", "M2", "--out", str(out)]
    assert main(argv) == 2
    assert not out.exists()
    manifest = build(raw, 2025, "M2", out, unlock_test="final report run, method v1")
    assert manifest["unlock_test_reason"] == "final report run, method v1"
    assert manifest["split"] == "test"
    assert json.loads((out / "bench_2025_M2.manifest.json").read_text())["unlock_test_reason"] == "final report run, method v1"
    assert main(argv + ["--unlock-test", "again"]) == 0


def test_a_later_year_in_the_raw_dir_is_never_read(raw, tmp_path):
    write_year(raw, 2025, [], columns=["not", "a", "faa", "file"])  # would raise if it were opened
    manifest, _, _ = run(raw, tmp_path)
    assert [s["year"] for s in manifest["sources"]] == [2024]


# ---- reproducibility ---------------------------------------------------------------------------------

def test_same_seed_gives_identical_bytes_and_another_seed_changes_presumed_negatives(raw, tmp_path):
    _, rows_a, out_a = run(raw, tmp_path, name="a", negatives=5, seed=1)
    _, _, out_b = run(raw, tmp_path, name="b", negatives=5, seed=1)
    for name in ("bench_2024_M1.jsonl", "bench_2024_M1.manifest.json", "presumed_negatives_check_2024.csv"):
        assert (out_a / name).read_bytes() == (out_b / name).read_bytes()
    _, rows_c, _ = run(raw, tmp_path, name="c", negatives=5, seed=2)
    pick = lambda rows: sorted(r["pair_id"] for r in rows if r["kind"] == "presumed_negative")
    assert pick(rows_a) != pick(rows_c)


def test_check_sheet_is_unmasked_identical_across_maskings_and_has_an_empty_answer_column(raw, tmp_path):
    _, _, out1 = run(raw, tmp_path, "M1", name="a")
    _, _, out2 = run(raw, tmp_path, "M2", name="b")
    sheet = out1 / "presumed_negatives_check_2024.csv"
    assert sheet.read_bytes() == (out2 / sheet.name).read_bytes()
    rows = list(csv.DictReader(sheet.open(encoding="utf-8")))
    assert 0 < len(rows) <= 50
    assert all(r["is_really_a_correction"] == "" and r["new_text"] and r["prior_text"] for r in rows)
    assert rows[0].keys() >= {"new_record_id", "prior_record_id", "tail", "new_part_name", "prior_jasc_code"}
