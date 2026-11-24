import json
import shutil

import pytest

from integrity.bench import run as bench_run
from integrity.bench.build import build
from integrity.bench.run import (
    LeakageError, TestSplitLockedError, candidate_report, classify_pairs, main, make_service,
    predictions_file, run_candidates, run_classify, select_pairs, system_report,
)
from services.conflict_engine import CASCADE_SCREEN_THRESHOLD
from tests.test_integrity_bench_build import CHAIN, MANY, SAME_MOMENT, SIBLINGS, write_year

ROWS = CHAIN + SIBLINGS + SAME_MOMENT + MANY
CITED_IDS = ("AAAA000001", "AAAA000002", "DDDD000001", "HHHH000001")


class FakeModel:
    """Records every prompt it is sent; answers with a fixed label, or fails for texts holding `fail_on`."""

    model = "fake-model"

    def __init__(self, label="supersedes", fail_on=None):
        self.label, self.fail_on = label, fail_on
        self.prompts = []  # (system, user)

    def extract_json_with_usage(self, prompt, system_prompt=None, max_tokens=800):
        self.prompts.append((system_prompt, prompt))
        if self.fail_on and self.fail_on in prompt:
            raise RuntimeError("model unreachable")
        return {
            "content": json.dumps({"label": self.label, "rationale": "r"}),
            "usage": {"prompt_tokens": 10, "completion_tokens": 2, "reasoning_tokens": 0, "total_tokens": 12},
        }


@pytest.fixture
def benches(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    write_year(raw, 2024, ROWS)
    for masking in ("M1", "M2"):
        build(raw, 2024, masking, tmp_path / "bench")
    return tmp_path / "bench"


def bench_file(benches, masking="M2"):
    return benches / f"bench_2024_{masking}.jsonl"


def run(benches, tmp_path, llm, masking="M2", **options):
    settings = dict(
        model="fake-model", prompt="v1", mode="cascade", passes=5, predictions_dir=tmp_path / "preds",
        out_path=tmp_path / "out.json", seed=1, test_log_path=tmp_path / "test_log.jsonl",
    )
    settings.update(options)
    return run_classify(bench_file(benches, masking), llm, **settings)


def rows_of(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


# ---- leakage -------------------------------------------------------------------------------

def test_citation_never_reaches_the_model(benches, tmp_path):
    for masking in ("M1", "M2"):
        source_text = " ".join(r["Discrepancy"] for r in ROWS).upper()
        assert "SUPPLEMENTAL REPORT FOR" in source_text and "(OPEN)" in source_text and "(CLOSED)" in source_text
        llm = FakeModel()
        report = run(benches, tmp_path, llm, masking=masking, out_path=tmp_path / f"{masking}.json",
                     predictions_dir=tmp_path / f"preds_{masking}")
        assert report["n_pairs_scored"] > 0 and llm.prompts
        for system, user in llm.prompts:
            seen = (system + "\n" + user).upper()
            assert "SUPPLEMENTAL REPORT FOR" not in seen
            assert not any(cited in seen for cited in CITED_IDS)
            if masking == "M2":
                assert "WILL BE SUBMITTED" not in seen
                assert "(OPEN)" not in seen and "(CLOSED)" not in seen


def test_a_row_that_still_holds_a_citation_raises_before_any_model_call(benches, tmp_path):
    rows = rows_of(bench_file(benches))
    rows[-1]["new"]["text"] += " SUPPLEMENTAL REPORT FOR ZZZZ999999: LATE"  # the last row: no earlier model call allowed
    path = tmp_path / "leaky.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    shutil.copy(benches / "bench_2024_M2.manifest.json", tmp_path / "leaky.manifest.json")
    llm = FakeModel()
    with pytest.raises(LeakageError, match="citation"):
        run_classify(path, llm, model="m", prompt="v1", mode="cascade", passes=5,
                     predictions_dir=tmp_path / "preds", out_path=tmp_path / "o.json", seed=1)
    assert llm.prompts == []


def test_m2_run_rejects_a_leftover_open_marker(benches, tmp_path):
    rows = rows_of(bench_file(benches))
    rows[0]["prior"]["text"] += " (OPEN)"
    with pytest.raises(LeakageError, match="status_marker"):
        classify_pairs(rows, FakeModel(), masking="M2", mode="cascade", prompt="v1", passes=5,
                       predictions_path=tmp_path / "p.jsonl", seed=1, limit=None)


# ---- stage 1 -------------------------------------------------------------------------------

def test_candidate_report_on_hand_built_rows():
    def positive(legacy, capped, n, reason=None):
        ranks = {"legacy": legacy, "containment": 1, "submission_gap": legacy}
        return {
            "kind": "positive", "ranks": ranks, "ranks_ignoring_chain": ranks,
            "ranks_capped": {**ranks, "legacy": capped}, "n_candidates": n, "not_candidate_reason": reason,
        }

    rows = [positive(1, 1, 1), positive(4, None, 4), positive(None, None, 2, "score_zero"),
            positive(None, None, 0, "not_strictly_earlier"), {"kind": "hard_negative"}]
    report = candidate_report(rows, seed=1)
    cells = report["hit_rates"]["ranks"]["legacy"]
    assert report["n_positives"] == 4
    assert cells["at_1"]["value"] == 1 / 4 and cells["at_3"]["value"] == 1 / 4
    assert cells["at_5"]["value"] == 2 / 4 and cells["anywhere"]["value"] == 2 / 4
    assert report["hit_rates"]["ranks_capped"]["legacy"]["anywhere"]["value"] == 1 / 4
    assert report["hit_rates"]["ranks"]["containment"]["at_1"]["value"] == 1.0
    assert report["prior_not_a_candidate"] == {
        "share": 2 / 4, "share_by_reason": {"not_strictly_earlier": 1 / 4, "score_zero": 1 / 4},
    }
    assert report["hidden_by_history_cap_share"] == 1 / 4
    assert report["n_candidates"] == {"median": 1.5, "p90": 4, "max": 4}
    assert report["mean_classified_per_report"] == {"top_1": 3 / 4, "top_3": (1 + 3 + 2 + 0) / 4}


def test_candidates_command_writes_sorted_json_without_report_text(benches, tmp_path, capsys):
    out = tmp_path / "candidates.json"
    assert main(["candidates", "--bench", str(bench_file(benches)), "--out", str(out)]) == 0
    text = out.read_text()
    result = json.loads(text)
    assert text == json.dumps(result, indent=2, sort_keys=True) + "\n"
    meta = result["meta"]
    assert meta["bench_file"] == "bench_2024_M2.jsonl" and meta["split"] == "select" and meta["masking"] == "M2"
    assert len(meta["manifest_sha256"]) == 64 and meta["n_resamples"] == 1000 and meta["model"] is None
    assert {"git_commit", "git_dirty", "created_at_utc", "seed"} <= set(meta)
    for row in ROWS:
        assert row["Discrepancy"] not in text
    assert "positives:" in capsys.readouterr().out
    assert run_candidates(bench_file(benches), out, seed=5)["meta"]["seed"] == 5


# ---- stage 2 -------------------------------------------------------------------------------

def record(label, kind, screen_score, predicted="supersedes", passes=2, seconds=3.0, parse_failed=False):
    return {
        "pair_id": f"{kind}-{label}-{screen_score}-{predicted}", "kind": kind, "label": label,
        "predicted_label": predicted, "parse_failed": parse_failed, "passes": passes, "seconds": seconds,
        "screen": {"screen_score": screen_score},
    }


def test_cascade_as_deployed_predicts_negative_below_the_threshold_with_zero_calls():
    records = [
        record(1, "positive", CASCADE_SCREEN_THRESHOLD - 0.01),
        record(1, "positive", CASCADE_SCREEN_THRESHOLD),
        record(0, "hard_negative", 0.1, predicted="partial_supersedes", passes=5),
        record(0, "presumed_negative", 0.95, predicted="no_conflict", parse_failed=True),
    ]
    model = system_report(records, cascaded=False, seed=1)
    cascade = system_report(records, cascaded=True, seed=1)
    assert model["confusion"] == {"tp": 2, "fp": 1, "fn": 0, "tn": 1}
    assert cascade["confusion"] == {"tp": 1, "fp": 0, "fn": 1, "tn": 2}
    assert model["model_calls_per_pair"]["mean"] == (2 + 2 + 5 + 2) / 4
    assert cascade["model_calls_per_pair"] == {"mean": (0 + 2 + 0 + 2) / 4, "median": 1.0}
    assert cascade["seconds_per_pair"]["mean"] == (0 + 3 + 0 + 3) / 4
    assert cascade["label_counts"] == {"no_conflict": 1, "screened_out": 2, "supersedes": 1}
    assert model["parse_failure_rate"] == 1 / 4
    assert model["false_link_rate_hard_negatives"]["value"] == 1.0
    assert model["false_link_rate_presumed_negatives"]["value"] == 0.0
    assert model["recall"]["value"] == 1.0 and cascade["recall"]["value"] == 1 / 2


def test_classify_writes_predictions_without_text_and_a_full_report(benches, tmp_path, capsys):
    llm = FakeModel()
    report = run(benches, tmp_path, llm, mode="legacy", passes=3)
    path = predictions_file(tmp_path / "preds", bench_file(benches), "fake-model", "v1", "legacy")
    stored = rows_of(path)
    assert len(stored) == report["n_pairs_scored"] == len(rows_of(bench_file(benches)))
    assert set(stored[0]) == {
        "pair_id", "kind", "label", "predicted_label", "parse_failed", "passes", "vote_agreement", "vote_split",
        "seconds", "tokens", "screen", "ranks",
    }
    assert stored[0]["passes"] == 3 and stored[0]["tokens"]["total_tokens"] == 36
    blob = path.read_text()
    for row in ROWS:
        assert row["Discrepancy"] not in blob
    assert report["meta"]["model"] == "fake-model" and report["meta"]["mode"] == "legacy"
    assert set(report["systems"]) == {"model", "cascade_as_deployed"}
    assert report["systems"]["model"]["recall"]["value"] == 1.0  # the fake always says supersedes
    assert json.loads((tmp_path / "out.json").read_text())["n_pairs_selected"] == report["n_pairs_selected"]


def test_a_second_run_makes_no_model_call_for_pairs_already_predicted(benches, tmp_path):
    first = FakeModel()
    run(benches, tmp_path, first)
    assert first.prompts
    second = FakeModel()
    run(benches, tmp_path, second)
    assert second.prompts == []


def test_an_errored_pair_is_reported_not_stored_and_retried(benches, tmp_path):
    rows = rows_of(bench_file(benches))
    flaky = FakeModel(fail_on=rows[0]["prior"]["text"][:30])
    report = run(benches, tmp_path, flaky)
    failed = {e["pair_id"] for e in report["errors"]}
    assert failed and all("model unreachable" in e["error"] for e in report["errors"])
    stored = rows_of(predictions_file(tmp_path / "preds", bench_file(benches), "fake-model", "v1", "cascade"))
    assert failed.isdisjoint(r["pair_id"] for r in stored)
    assert report["n_pairs_scored"] == len(rows) - len(failed)
    retry = FakeModel()
    report = run(benches, tmp_path, retry)
    assert report["errors"] == [] and report["n_pairs_scored"] == len(rows)
    assert len(retry.prompts) >= len(failed)


def test_limit_takes_the_same_pairs_for_the_same_seed(benches):
    rows = rows_of(bench_file(benches))
    ids = lambda picked: [r["pair_id"] for r in picked]  # noqa: E731
    a = select_pairs(rows, seed=3, limit=7)
    assert ids(a) == ids(select_pairs(rows, seed=3, limit=7))
    assert len(a) == 7 and set(ids(a)) <= set(ids(rows))
    assert ids(a) != ids(rows[:7]) and ids(a) != ids(select_pairs(rows, seed=4, limit=7))
    assert ids(select_pairs(rows, seed=3, limit=None)) == ids(rows)


def test_time_first_times_pairs_prints_a_projection_and_writes_nothing(benches, tmp_path, capsys):
    llm = FakeModel()
    assert run(benches, tmp_path, llm, time_first=2) is None
    assert len(llm.prompts) >= 4  # cascade asks at least twice per pair
    assert "projected" in capsys.readouterr().out
    assert not (tmp_path / "out.json").exists() and not (tmp_path / "preds").exists()


# ---- the test split ------------------------------------------------------------------------

@pytest.fixture
def test_split_bench(benches, tmp_path):
    manifest = json.loads((benches / "bench_2024_M2.manifest.json").read_text())
    manifest["split"] = "test"
    directory = tmp_path / "locked"
    directory.mkdir()
    shutil.copy(bench_file(benches), directory / "bench_2025_M2.jsonl")
    (directory / "bench_2025_M2.manifest.json").write_text(json.dumps(manifest))
    return directory / "bench_2025_M2.jsonl"


def test_the_test_split_is_refused_without_a_reason_and_logged_with_one(test_split_bench, tmp_path):
    log, llm = tmp_path / "log.jsonl", FakeModel()
    options = dict(model="fake-model", prompt="v1", mode="cascade", passes=5, predictions_dir=tmp_path / "p",
                   out_path=tmp_path / "o.json", seed=1, test_log_path=log)
    with pytest.raises(TestSplitLockedError):
        run_classify(test_split_bench, llm, **options)
    with pytest.raises(TestSplitLockedError):
        run_classify(test_split_bench, llm, unlock_test="   ", **options)
    assert llm.prompts == [] and not log.exists()

    run_classify(test_split_bench, llm, unlock_test="first and only run of method v1", limit=3, **options)
    lines = rows_of(log)
    assert len(lines) == 1
    assert {k: lines[0][k] for k in ("file", "model", "prompt", "reason")} == {
        "file": "bench_2025_M2.jsonl", "model": "fake-model", "prompt": "v1", "reason": "first and only run of method v1",
    }
    assert "commit" in lines[0]
    assert llm.prompts


def test_main_refuses_the_test_split_with_exit_code_2(test_split_bench, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(bench_run, "make_service", lambda *args: FakeModel())
    code = main(["classify", "--bench", str(test_split_bench), "--model", "m", "--base-url", "http://x/v1",
                 "--predictions", str(tmp_path / "p"), "--out", str(tmp_path / "o.json")])
    assert code == 2 and "held-out test split" in capsys.readouterr().err


# ---- the service ---------------------------------------------------------------------------

def test_make_service_refuses_a_service_that_is_not_live():
    with pytest.raises(RuntimeError, match="not live"):
        make_service("m", "", "local")
    assert make_service("m", "http://localhost:11434/v1", "local").is_live
