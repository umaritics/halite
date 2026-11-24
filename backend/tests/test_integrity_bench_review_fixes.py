"""Scenarios from the review of the benchmark, each written to fail on the code that was reviewed."""
import json
import shutil
from collections import Counter

import pytest

from integrity.bench.build import build, operator_quotas
from integrity.bench.masking import leaks, mask_text
from integrity.bench.run import (
    PredictionsMismatchError, TestSplitLockedError, main, read_predictions, run_candidates, run_classify,
    system_report,
)
from tests.test_integrity_bench_build import at, faa, write_year
from tests.test_integrity_bench_run import ROWS, FakeModel, bench_file, rows_of

PRIOR_TEXT = "AIRCRAFT WAS NOT GROUNDED: OVEN 1 SMOKING DURING USE"


def build_year(tmp_path, rows, name="out", masking="M2", year=2024, **options):
    raw = tmp_path / f"raw_{name}"
    raw.mkdir(exist_ok=True)
    write_year(raw, year, rows)
    out = tmp_path / name
    manifest = build(raw, year, masking, out, **options)
    bench = [json.loads(line) for line in (out / f"bench_{year}_{masking}.jsonl").read_text().splitlines()]
    return manifest, bench, out


# ---- masking leaves nothing structural behind -------------------------------------------------

@pytest.mark.parametrize("masking", ("M1", "M2"))
def test_no_asterisk_survives_the_announcement_seam(masking):
    text = f"{PRIOR_TEXT}. **SUPPLEMENTAL REPORT FOR (AALA202301039115):** REMOVED AND REPLACED OVEN 1 **"
    masked = mask_text(text, masking, ("AALA202301039115",))
    assert "*" not in masked and "REMOVED AND REPLACED OVEN 1" in masked
    assert leaks(masked, masking) == []
    assert leaks("A ** B", masking) == ["emphasis_marks"]


@pytest.mark.parametrize("phrase", [
    "SUPPLEMENTAL REPORT REQUIRED",
    "SUUPLEMENTAL REPORT WILL BE SUBMITTTED",
    "SUPPLEMENTAL REPORT WIL BE SUBMITTED",
    "SUPPLEMENTAL REPORT WAS SUBMITTED",
    "SUPPLEMENTAL REPORT FOR THE #1",
    "SUPPLEMENATAL REPORT FOR SDR AALA202301039115",
    "SUPPLEMENTAL REPORTFOR AALA202301039115",
])
def test_m2_removes_every_wording_of_the_open_sentence_and_nothing_else(phrase):
    masked = mask_text(f"OVEN SMOKING. **{phrase}.** (OPEN) OVEN REPLACED", "M2")
    assert masked == "OVEN SMOKING. OVEN REPLACED"
    assert leaks(masked, "M2") == []


def test_m2_keeps_words_that_only_look_like_the_phrase_and_leaks_sees_a_loose_survivor():
    assert mask_text("SUPPORT REPLACED, SUPPLY REPAIRED", "M2") == "SUPPORT REPLACED, SUPPLY REPAIRED"
    assert leaks("A SUPPLEMENTAL, REPORT B", "M2") == ["open_marker"]


@pytest.mark.parametrize("masking", ("M1", "M2"))
def test_a_resubmission_naming_the_original_leaves_no_marker(masking):
    masked = mask_text("OVEN SMOKING. **ORIGINAL REPORT WAS AALA202302204012** REPLACED OVEN", masking)
    assert masked == "OVEN SMOKING. REPLACED OVEN"
    assert leaks("X ORIGINAL REPORT WAS AALA202302204012", masking) == ["citation"]
    assert leaks("THE ORIGINAL REPORT WAS LATE", masking) == []


# ---- builder: fair negatives -------------------------------------------------------------------

ORIGINAL = faa("AALA000001", "N1", at("01-01"), "AIRCRAFT WAS GROUNDED: PUMP SEAL LEAK ON LEFT PUMP")
NEW = faa("AALA000003", "N1", at("01-09"),
          "AIRCRAFT WAS GROUNDED: PUMP SEAL LEAK ON LEFT PUMP. **SUPPLEMENTAL REPORT FOR (AALA000001):** SEAL REPLACED")
SIBLING = faa("AALA000002", "N1", at("01-05"),
              "AIRCRAFT WAS GROUNDED: PUMP SEAL LEAK ON LEFT PUMP. **ORIGINAL REPORT WAS AALA000001** SEAL REPLACED")
UNRELATED = faa("AALA000009", "N1", at("01-02"), "CABIN LIGHT FLICKERS ON LEFT PUMP PANEL")


def test_a_resubmission_of_the_same_original_is_not_a_hard_negative(tmp_path):
    manifest, bench, _ = build_year(tmp_path, [ORIGINAL, SIBLING, NEW, UNRELATED])
    hard = {r["prior"]["record_id"] for r in bench if r["kind"] == "hard_negative"}
    assert "AALA000002" not in hard and hard == {"AALA000009"}
    assert manifest["hard_negatives_dropped_as_related"] >= 1
    for row in bench:
        assert "ORIGINAL REPORT" not in row["prior"]["text"] and "ORIGINAL REPORT" not in row["new"]["text"]


def test_a_candidate_whose_text_names_the_new_report_is_not_a_hard_negative(tmp_path):
    names_new = faa("AALA000008", "N1", at("01-03"), "PUMP SEAL LEAK ON LEFT PUMP SEE AALA000003 FOR REPAIR")
    _, bench, _ = build_year(tmp_path, [ORIGINAL, names_new, NEW, UNRELATED])
    assert "AALA000008" not in {r["prior"]["record_id"] for r in bench if r["kind"] == "hard_negative"}


def test_the_same_id_rule_holds_for_every_kind(tmp_path):
    work_order = faa("AALA000001", "N1", at("01-01"), "PUMP SEAL LEAK ON LEFT PUMP WO AALA000001")
    new = faa("AALA000003", "N1", at("01-09"), "PUMP SEAL LEAK ON LEFT PUMP. SUPPLEMENTAL REPORT FOR AALA000001: FIXED WO AALA000001")
    other = faa("AALA000009", "N1", at("01-02"), "CABIN LIGHT ON LEFT PUMP PANEL WO AALA000009")
    _, bench, _ = build_year(tmp_path, [work_order, new, other])
    assert {r["kind"] for r in bench} >= {"positive", "hard_negative"}
    for row in bench:
        for side in ("new", "prior"):
            assert row[side]["record_id"] not in row[side]["text"], row["pair_id"]
            assert row["new" if side == "prior" else "prior"]["record_id"] not in row[side]["text"]


def test_presumed_negatives_never_name_each_other(tmp_path):
    rows = [
        faa(f"BBBB{n:06d}", "N5", at(f"02-0{n}"), f"PUMP SEAL LEAK ON LEFT PUMP NOTE {n}" + (" SAME AS BBBB000001" if n == 2 else ""))
        for n in range(1, 6)
    ]
    manifest, bench, _ = build_year(tmp_path, [ORIGINAL, NEW] + rows, negatives=10)
    for row in (r for r in bench if r["kind"] == "presumed_negative"):
        assert {row["new"]["record_id"], row["prior"]["record_id"]} != {"BBBB000002", "BBBB000001"}
    assert manifest["presumed_negatives_skipped_as_related"] >= 1


def test_pool_leaves_out_corrections_the_parser_cannot_read(tmp_path):
    unread = [
        faa("CCCC000001", "N6", at("03-01"), "PUMP SEAL LEAK"),
        faa("CCCC000002", "N6", at("03-02"), "PUMP SEAL LEAK SUPPLEMENTAL REPORT FOR SDR CCCC000001 DONE"),
        faa("CCCC000003", "N6", at("03-03"), "PUMP SEAL LEAK SUPPLEMENATAL REPORT FOR CCCC000001"),
        faa("CCCC000004", "N6", at("03-04"), "PUMP SEAL LEAK ORIGINAL REPORT WAS CCCC000001"),
        faa("CCCC000005", "N6", at("03-05"), "PUMP SEAL LEAK"),
    ]
    manifest, bench, _ = build_year(tmp_path, [ORIGINAL, NEW] + unread, negatives=10)
    drawn = {r["new"]["record_id"] for r in bench if r["kind"] == "presumed_negative"}
    assert drawn <= {"CCCC000005"}
    assert manifest["presumed_pool_left_out_unparsed_correction"] == 3


def test_presumed_negatives_follow_the_operator_mix_of_the_positives(tmp_path):
    rows = []
    for index, op in enumerate(("AALA", "SWAA", "DALA")):
        for n in range(2):
            tail = f"T{index}{n}"
            rows.append(faa(f"{op}{n + 5}00001", tail, at("04-01"), "PUMP SEAL LEAK ON LEFT PUMP"))
            rows.append(faa(f"{op}{n + 5}00002", tail, at("04-02"), "PUMP SEAL LEAK ON LEFT PUMP"))
    manifest, bench, _ = build_year(tmp_path, [ORIGINAL, NEW] + rows, negatives=2)
    presumed = [r["new"]["record_id"][:4] for r in bench if r["kind"] == "presumed_negative"]
    assert presumed == ["AALA", "AALA"] and manifest["presumed_negatives_from_other_operators"] == 0
    assert manifest["operator_mix"]["positive"] == {"AALA": 1}
    assert manifest["operator_mix"]["presumed_negative"] == {"AALA": 2}


def test_a_missing_operator_is_filled_from_the_rest_and_counted(tmp_path):
    rows = [faa(f"SWAA{n:06d}", "N8", at(f"05-0{n}"), f"PUMP SEAL LEAK ON LEFT PUMP NOTE {n}") for n in range(1, 4)]
    manifest, bench, _ = build_year(tmp_path, [ORIGINAL, NEW] + rows, negatives=2)
    assert manifest["counts"]["presumed_negative"] == 2
    assert manifest["presumed_negatives_from_other_operators"] == 2


def test_operator_quotas_use_largest_remainder():
    assert operator_quotas(Counter({"A": 2, "B": 1}), 4) == {"A": 3, "B": 1}
    assert operator_quotas(Counter({"A": 1, "B": 1}), 3) == {"A": 2, "B": 1}
    assert operator_quotas(Counter(), 5) == {}


# ---- the runner: resume, test split, honesty ------------------------------------------------------

@pytest.fixture
def bench(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    from tests.test_integrity_bench_build import write_year as write
    write(raw, 2024, ROWS)
    build(raw, 2024, "M2", tmp_path / "bench")
    return tmp_path / "bench" / "bench_2024_M2.jsonl"


def classify(bench, tmp_path, llm=None, **overrides):
    options = dict(model="fake-model", prompt="v1", mode="legacy", passes=3, predictions_dir=tmp_path / "preds",
                   out_path=tmp_path / "o.json", seed=1, base_url="http://a/v1", test_log_path=tmp_path / "log.jsonl")
    options.update(overrides)
    return run_classify(bench, llm or FakeModel(), **options)


@pytest.mark.parametrize("change", [{"passes": 5}, {"base_url": "http://b/v1"}])
def test_a_changed_configuration_does_not_reuse_stored_predictions(bench, tmp_path, change):
    classify(bench, tmp_path)
    llm = FakeModel()
    with pytest.raises(PredictionsMismatchError):
        classify(bench, tmp_path, llm, **change)
    assert llm.prompts == []


def test_model_names_that_share_a_file_name_do_not_share_predictions(bench, tmp_path):
    classify(bench, tmp_path, model="phi4:mini")
    with pytest.raises(PredictionsMismatchError):
        classify(bench, tmp_path, FakeModel(), model="phi4_mini")


def test_a_rebuilt_bench_does_not_reuse_stored_predictions(bench, tmp_path):
    classify(bench, tmp_path)
    lines = bench.read_text().splitlines(keepends=True)
    row = json.loads(lines[0])
    row["prior"]["text"] += " EDITED"
    bench.write_text("".join([json.dumps(row) + "\n"] + lines[1:]))
    with pytest.raises(PredictionsMismatchError):
        classify(bench, tmp_path)


def test_cascade_mode_ignores_passes_and_the_same_configuration_resumes(bench, tmp_path):
    classify(bench, tmp_path, mode="cascade", passes=3)
    again = FakeModel()
    classify(bench, tmp_path, again, mode="cascade", passes=9)
    assert again.prompts == []


def test_the_bench_hash_is_in_meta(bench, tmp_path):
    assert len(classify(bench, tmp_path)["meta"]["bench_sha256"]) == 64
    assert len(run_candidates(bench, tmp_path / "c.json", seed=1)["meta"]["bench_sha256"]) == 64


def test_a_run_killed_mid_write_resumes(bench, tmp_path):
    classify(bench, tmp_path)
    path = next((tmp_path / "preds").glob("*.jsonl"))
    complete = path.read_text().splitlines(keepends=True)
    path.write_text("".join(complete[:-1]) + '{"pair_id":"c|d","x"')
    assert len(read_predictions(path)) == len(complete) - 1
    assert path.read_text() == "".join(complete[:-1])
    llm = FakeModel()
    report = classify(bench, tmp_path, llm)
    assert report["n_pairs_scored"] == len(complete) and llm.prompts


@pytest.fixture
def test_split_bench(bench, tmp_path):
    manifest = json.loads(bench.with_suffix(".manifest.json").read_text())
    manifest["split"] = "test"
    directory = tmp_path / "locked"
    directory.mkdir()
    shutil.copy(bench, directory / "bench_2025_M2.jsonl")
    (directory / "bench_2025_M2.manifest.json").write_text(json.dumps(manifest))
    return directory / "bench_2025_M2.jsonl"


def test_stage_1_on_the_test_split_needs_a_reason_and_is_logged(test_split_bench, tmp_path, capsys):
    log = tmp_path / "log.jsonl"
    with pytest.raises(TestSplitLockedError):
        run_candidates(test_split_bench, tmp_path / "x.json", seed=1, test_log_path=log)
    assert not log.exists() and not (tmp_path / "x.json").exists()
    assert main(["candidates", "--bench", str(test_split_bench), "--out", str(tmp_path / "x.json")]) == 2
    assert "held-out test split" in capsys.readouterr().err
    run_candidates(test_split_bench, tmp_path / "x.json", seed=1, unlock_test="stage 1, method v1", test_log_path=log)
    (line,) = rows_of(log)
    assert line["stage"] == "candidates" and line["reason"] == "stage 1, method v1" and line["seed"] == 1 and line["at_utc"]


def test_a_classify_log_line_says_how_the_run_was_set_up(test_split_bench, tmp_path):
    log = tmp_path / "log.jsonl"
    classify(test_split_bench, tmp_path, unlock_test="why", limit=2, test_log_path=log)
    (line,) = rows_of(log)
    assert {k: line[k] for k in ("stage", "mode", "passes", "limit", "seed")} == {
        "stage": "classify", "mode": "legacy", "passes": 3, "limit": 2, "seed": 1,
    }


def test_system_report_says_every_pair_is_assumed_to_reach_the_model():
    record = {"pair_id": "a|b", "kind": "positive", "label": 1, "predicted_label": "supersedes", "parse_failed": False,
              "passes": 2, "seconds": 1.0, "screen": {"screen_score": 1.0}}
    assert system_report([record], cascaded=True, seed=1)["assumes_every_pair_reaches_the_model"] is True
