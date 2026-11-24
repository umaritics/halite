"""Run the citation-masked benchmark: stage 1 (candidates, no model) and stage 2 (classify, the model).

Run from backend/:
  python -m integrity.bench.run candidates --bench <bench.jsonl> --out integrity/bench/results/candidates_2024_M2.json
  python -m integrity.bench.run classify --bench <bench.jsonl> --model phi4-mini --base-url http://localhost:11434/v1 \
      --prompt v1 --mode cascade --predictions <dir> --out integrity/bench/results/classify_2024_M2_phi4-mini_v1.json

Every number comes out of these runs into the result files; nothing is written down by hand.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import statistics
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from integrity.bench import metrics
from integrity.bench.build import DEFAULT_SEED
from integrity.bench.masking import leaks
from integrity.candidates import ORDERINGS
from integrity.classify import classify_pair
from integrity.prompts import CLASSIFICATION_PROMPTS
from services.conflict_engine import CASCADE_SCREEN_THRESHOLD

RESULTS_DIR = Path(__file__).resolve().parent / "results"
TEST_LOG_PATH = RESULTS_DIR / "test_split_log.jsonl"
N_RESAMPLES = 1000
REQUEST_TIMEOUT_S = 120.0
RANK_KEYS = ("ranks", "ranks_ignoring_chain", "ranks_capped")
HIT_CUTOFFS = (("at_1", 1), ("at_3", 3), ("at_5", 5), ("anywhere", None))
POSITIVE_LABELS = ("supersedes", "partial_supersedes")
TOKEN_KEYS = ("prompt_tokens", "completion_tokens", "reasoning_tokens", "total_tokens")


class TestSplitLockedError(RuntimeError):
    """The bench file is the held-out test year and no reason for opening it was given."""

    __test__ = False  # not a pytest class, despite the name


class PredictionsMismatchError(RuntimeError):
    """A predictions file was made with another bench, model, endpoint, prompt, mode or vote count."""


class LeakageError(ValueError):
    """A text the model would read still holds something masking should have removed."""


# ---- reading the bench and describing the run ---------------------------------------------

def load_bench(bench_path) -> tuple[list[dict], dict, Path]:
    """The rows, the manifest that sits beside them, and the manifest's path."""
    bench_path = Path(bench_path)
    manifest_path = bench_path.with_suffix(".manifest.json")
    rows = [json.loads(line) for line in bench_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return rows, json.loads(manifest_path.read_text(encoding="utf-8")), manifest_path


def git_state() -> tuple[str, bool | str]:
    """(commit, dirty); "unknown" when git cannot answer, so a result is never blocked by it."""
    here = str(Path(__file__).resolve().parent)

    def git(*args):
        return subprocess.run(["git", *args], cwd=here, capture_output=True, text=True, check=True).stdout.strip()

    try:
        return git("rev-parse", "HEAD"), bool(git("status", "--porcelain"))
    except (OSError, subprocess.CalledProcessError):
        return "unknown", "unknown"


def make_meta(bench_path, manifest_path, manifest, *, seed, model=None, prompt=None, mode=None) -> dict:
    commit, dirty = git_state()
    return {
        "bench_file": Path(bench_path).name,
        "bench_sha256": hashlib.sha256(Path(bench_path).read_bytes()).hexdigest(),
        "manifest_sha256": hashlib.sha256(Path(manifest_path).read_bytes()).hexdigest(),
        "manifest_counts": manifest["counts"],
        "positives_hidden_by_history_cap": manifest["positives_hidden_by_history_cap"],
        "split": manifest["split"],
        "masking": manifest["masking"],
        "seed": seed,
        "n_resamples": N_RESAMPLES,
        "model": model,
        "prompt_version": prompt,
        "mode": mode,
        "git_commit": commit,
        "git_dirty": dirty,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def write_json(path, payload: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _interval(items, statistic, seed: int) -> dict:
    low, high = metrics.bootstrap_interval(items, statistic, n_resamples=N_RESAMPLES, seed=seed)
    return {"value": statistic(items), "low": low, "high": high}


def _pct(value) -> str:
    return "n/a" if value is None else f"{100 * value:.1f}%"


# ---- stage 1: candidates -------------------------------------------------------------------

def candidate_report(rows: list[dict], *, seed: int) -> dict:
    """Where the true prior lands, for positives only; negatives have no true prior to find."""
    positives = [r for r in rows if r["kind"] == "positive"]
    hit_rates = {
        key: {
            ordering: {
                name: _interval(
                    positives, lambda items, key=key, ordering=ordering, k=k: metrics.hit_rate(items, key, ordering, k), seed
                )
                for name, k in HIT_CUTOFFS
            }
            for ordering in ORDERINGS
        }
        for key in RANK_KEYS
    }
    n = len(positives)
    reasons = Counter(r["not_candidate_reason"] for r in positives if r["not_candidate_reason"])
    sizes = [r["n_candidates"] for r in positives]
    hidden = sum(r["ranks"]["legacy"] is not None and r["ranks_capped"]["legacy"] is None for r in positives)
    return {
        "n_positives": n,
        "hit_rates": hit_rates,
        "prior_not_a_candidate": {
            "share": sum(reasons.values()) / n if n else None,
            "share_by_reason": {reason: count / n for reason, count in sorted(reasons.items())},
        },
        "hidden_by_history_cap_share": hidden / n if n else None,
        "n_candidates": (
            {"median": statistics.median(sizes), "p90": metrics.percentile(sizes, 0.9), "max": max(sizes)} if sizes else None
        ),
        "mean_classified_per_report": (
            {"top_1": statistics.mean(min(s, 1) for s in sizes), "top_3": statistics.mean(min(s, 3) for s in sizes)}
            if sizes else None
        ),
    }


def candidate_summary(report: dict) -> str:
    lines = [f"positives: {report['n_positives']}"]
    for key, by_ordering in report["hit_rates"].items():
        for ordering, cells in by_ordering.items():
            parts = [f"{name} {_pct(cell['value'])} [{_pct(cell['low'])}, {_pct(cell['high'])}]" for name, cell in cells.items()]
            lines.append(f"{key:<21}{ordering:<15}" + "  ".join(parts))
    missing = report["prior_not_a_candidate"]
    reasons = ", ".join(f"{r} {_pct(s)}" for r, s in missing["share_by_reason"].items()) or "none"
    lines.append(f"true prior not a candidate: {_pct(missing['share'])} ({reasons})")
    lines.append(f"hidden by the history cap: {_pct(report['hidden_by_history_cap_share'])}")
    if report["n_candidates"]:
        sizes, cost = report["n_candidates"], report["mean_classified_per_report"]
        lines.append(f"n_candidates median {sizes['median']}, p90 {sizes['p90']}, max {sizes['max']}")
        lines.append(f"mean classified per report: top-1 {cost['top_1']:.2f}, top-3 {cost['top_3']:.2f}")
    return "\n".join(lines)


def run_candidates(bench_path, out_path, *, seed: int, unlock_test=None, test_log_path=None) -> dict:
    rows, manifest, manifest_path = load_bench(bench_path)
    refuse_test_split(
        manifest, bench_name=Path(bench_path).name, model=None, prompt=None, reason=unlock_test,
        log_path=test_log_path or TEST_LOG_PATH, details={"stage": "candidates", "seed": seed},
    )
    report = {"meta": make_meta(bench_path, manifest_path, manifest, seed=seed), **candidate_report(rows, seed=seed)}
    write_json(out_path, report)
    return report


# ---- stage 2: classify ---------------------------------------------------------------------

def make_service(model: str, base_url: str, api_key: str):
    """The same service object staging builds for an OpenAI-compatible endpoint."""
    from services.groq_service import GroqService

    service = GroqService(
        api_key, model=model, provider="openai_compatible",
        openai_compat_base_url=base_url, request_timeout_s=REQUEST_TIMEOUT_S,
    )
    if not service.is_live:
        raise RuntimeError("the model service is not live; refusing to benchmark a demo fallback")
    return service


def select_pairs(rows: list[dict], *, seed: int, limit: int | None) -> list[dict]:
    """All pairs in file order, or the first `limit` after a seeded shuffle so a short run is a fair sample."""
    if limit is None:
        return list(rows)
    shuffled = list(rows)
    random.Random(seed).shuffle(shuffled)
    return shuffled[:limit]


def check_no_leaks(rows: list[dict], masking: str) -> None:
    """Fail before any model call: one leaked citation would turn the benchmark into the circular one."""
    for row in rows:
        for side in ("new", "prior"):
            found = leaks(row[side]["text"], masking)
            if found:
                raise LeakageError(f"{row['pair_id']}: {side} text still leaks {found}")


def read_predictions(path: Path) -> dict[str, dict]:
    """Stored predictions by pair id. A last line cut short by a crash is dropped (and the file trimmed),
    so an interrupted run can always resume; its pair is simply classified again."""
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    if text and not text.endswith("\n"):
        text = text[: text.rfind("\n") + 1]
        path.write_text(text, encoding="utf-8", newline="\n")
        print(f"warning: dropped an unfinished last line of {path.name}", file=sys.stderr)
    records = [json.loads(line) for line in text.splitlines() if line.strip()]
    return {record["pair_id"]: record for record in records}


def classify_one(llm, row: dict, *, mode: str, prompt: str, passes: int) -> dict:
    """One prediction record. It holds ids, labels and timings, never report text."""
    started = time.perf_counter()
    result = classify_pair(llm, row["new"], row["prior"], analysis_mode=mode, passes=passes, prompt_version=prompt)
    return {
        "pair_id": row["pair_id"],
        "kind": row["kind"],
        "label": row["label"],
        "predicted_label": result["label"],
        "parse_failed": result["parse_failed"],
        "passes": result["passes"],
        "vote_agreement": result["vote_agreement"],
        "vote_split": result["vote_split"],
        "seconds": time.perf_counter() - started,
        "tokens": {key: result[key] for key in TOKEN_KEYS},
        "screen": row["screen"],
        "ranks": row["ranks"],
    }


def classify_pairs(rows, llm, *, masking, mode, prompt, passes, predictions_path, seed, limit):
    """Classify the selected pairs that have no prediction yet; return (selected, records by id, errors).

    A finished pair is appended at once, so an interrupted run resumes where it stopped. A pair whose
    model call fails is reported but not stored, so the next run tries it again.
    """
    selected = select_pairs(rows, seed=seed, limit=limit)
    check_no_leaks(selected, masking)
    predictions_path = Path(predictions_path)
    records = read_predictions(predictions_path)
    errors = []
    predictions_path.parent.mkdir(parents=True, exist_ok=True)
    for row in selected:
        if row["pair_id"] in records:
            continue
        try:
            record = classify_one(llm, row, mode=mode, prompt=prompt, passes=passes)
        except Exception as error:  # a model or network failure on one pair must not lose the others
            errors.append({"pair_id": row["pair_id"], "error": str(error)[:200]})
            continue
        with open(predictions_path, "a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        records[row["pair_id"]] = record
    return selected, records, errors


def system_report(records: list[dict], *, cascaded: bool, seed: int) -> dict:
    """Score one system. The cascade answers 'no' without a model call below the screen threshold, as staging does."""
    pairs, seconds, calls, labels = [], [], [], Counter()
    parse_failures = 0
    for record in records:
        screened = cascaded and record["screen"]["screen_score"] < CASCADE_SCREEN_THRESHOLD
        predicted = not screened and record["predicted_label"] in POSITIVE_LABELS
        pairs.append({"label": record["label"], "predicted": predicted, "kind": record["kind"]})
        seconds.append(0.0 if screened else record["seconds"])
        calls.append(0 if screened else record["passes"])
        labels["screened_out" if screened else record["predicted_label"]] += 1
        parse_failures += (not screened) and record["parse_failed"]

    def of_kind(*kinds):
        return [p for p in pairs if p["kind"] in kinds]

    scores = {
        "precision": metrics.precision, "recall": metrics.recall, "f1": metrics.f1,
        "false_link_rate": metrics.false_link_rate,
    }
    report = {name: _interval(pairs, fn, seed) for name, fn in scores.items()}
    report["false_link_rate_hard_negatives"] = _interval(of_kind("hard_negative"), metrics.false_link_rate, seed)
    report["false_link_rate_presumed_negatives"] = _interval(of_kind("presumed_negative"), metrics.false_link_rate, seed)
    report.update({
        # Staging classifies only its top candidate; here every pair is treated as having reached the model,
        # so stage 1 misses are not counted against recall. Read this with the stage 1 hit rates.
        "assumes_every_pair_reaches_the_model": True,
        "n_pairs": len(pairs),
        "confusion": metrics.confusion(pairs),
        "parse_failure_rate": parse_failures / len(pairs) if pairs else None,
        "label_counts": dict(sorted(labels.items())),
        "seconds_per_pair": {"mean": statistics.mean(seconds), "median": statistics.median(seconds)} if seconds else None,
        "model_calls_per_pair": {"mean": statistics.mean(calls), "median": statistics.median(calls)} if calls else None,
    })
    return report


def classify_report(selected, records, errors, *, seed) -> dict:
    scored = [records[row["pair_id"]] for row in selected if row["pair_id"] in records]
    return {
        "n_pairs_selected": len(selected),
        "n_pairs_scored": len(scored),
        "errors": errors,
        "systems": {
            "model": system_report(scored, cascaded=False, seed=seed),
            "cascade_as_deployed": system_report(scored, cascaded=True, seed=seed),
        },
    }


def classify_summary(report: dict) -> str:
    lines = [f"pairs scored {report['n_pairs_scored']} of {report['n_pairs_selected']}, errors {len(report['errors'])}",
             "every pair is assumed to reach the model; stage 1 misses are not counted"]
    for name, system in report["systems"].items():
        parts = []
        for metric in ("precision", "recall", "f1", "false_link_rate"):
            cell = system[metric]
            parts.append(f"{metric} {_pct(cell['value'])} [{_pct(cell['low'])}, {_pct(cell['high'])}]")
        lines.append(f"{name}: " + "  ".join(parts))
        seconds, calls = system["seconds_per_pair"], system["model_calls_per_pair"]
        if seconds:
            lines.append(
                f"  parse failures {_pct(system['parse_failure_rate'])}, {seconds['mean']:.2f} s and "
                f"{calls['mean']:.2f} calls per pair (mean)"
            )
    return "\n".join(lines)


def refuse_test_split(manifest: dict, *, bench_name, model, prompt, reason, log_path, details=None) -> None:
    """The test year is opened once per method version, so opening it needs a reason and leaves a line."""
    if manifest["split"] != "test":
        return
    reason = (reason or "").strip()
    if not reason:
        raise TestSplitLockedError(f"{bench_name} is the held-out test split; pass --unlock-test with the reason")
    commit, _ = git_state()
    line = {
        "file": bench_name, "model": model, "prompt": prompt, "reason": reason, "commit": commit,
        "at_utc": datetime.now(timezone.utc).isoformat(), **(details or {}),
    }
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(line, sort_keys=True) + "\n")


def predictions_file(directory, bench_path, model, prompt, mode) -> Path:
    safe_model = model.replace("/", "_").replace(":", "_")
    return Path(directory) / f"{Path(bench_path).stem}__{safe_model}__{prompt}__{mode}.jsonl"


def claim_predictions(path: Path, config: dict) -> None:
    """Tie a predictions file to the configuration that made it, or refuse to resume it.

    The file name is lossy (a/b and a_b look alike), so the exact configuration sits beside it.
    """
    config_path = path.with_name(path.name + ".config.json")
    if config_path.exists():
        if json.loads(config_path.read_text(encoding="utf-8")) != config:
            raise PredictionsMismatchError(f"{path.name} was made with another configuration; use a new --predictions directory")
    elif path.exists():
        raise PredictionsMismatchError(f"{path.name} has no configuration file; use a new --predictions directory")
    else:
        write_json(config_path, config)


def run_classify(bench_path, llm, *, model, prompt, mode, passes, predictions_dir, out_path, seed, limit=None,
                 time_first=None, unlock_test=None, test_log_path=None, base_url=None) -> dict | None:
    """Stage 2 end to end. With time_first the pairs are timed and nothing is written."""
    rows, manifest, manifest_path = load_bench(bench_path)
    refuse_test_split(
        manifest, bench_name=Path(bench_path).name, model=model, prompt=prompt, reason=unlock_test,
        log_path=test_log_path or TEST_LOG_PATH,
        details={"stage": "classify", "mode": mode, "passes": passes, "limit": limit, "seed": seed},
    )
    masking = manifest["masking"]
    if time_first is not None:
        sample = select_pairs(rows, seed=seed, limit=time_first)
        check_no_leaks(sample, masking)
        per_pair = [classify_one(llm, row, mode=mode, prompt=prompt, passes=passes)["seconds"] for row in sample]
        mean = statistics.mean(per_pair)
        total = len(select_pairs(rows, seed=seed, limit=limit))
        print(f"timed {len(per_pair)} pairs: {mean:.2f} s per pair; projected for {total} pairs: {mean * total / 3600:.2f} h")
        return None
    path = predictions_file(predictions_dir, bench_path, model, prompt, mode)
    claim_predictions(path, {
        "bench_sha256": hashlib.sha256(Path(bench_path).read_bytes()).hexdigest(), "model": model,
        "base_url": base_url, "prompt": prompt, "mode": mode, "passes": passes if mode == "legacy" else None,
    })
    selected, records, errors = classify_pairs(
        rows, llm, masking=masking, mode=mode, prompt=prompt, passes=passes,
        predictions_path=path, seed=seed, limit=limit,
    )
    report = {
        "meta": make_meta(bench_path, manifest_path, manifest, seed=seed, model=model, prompt=prompt, mode=mode),
        **classify_report(selected, records, errors, seed=seed),
    }
    write_json(out_path, report)
    return report


# ---- command line --------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--bench", required=True)
    shared.add_argument("--seed", type=int, default=DEFAULT_SEED)

    candidates = commands.add_parser("candidates", parents=[shared], help="stage 1, no model")
    candidates.add_argument("--out", required=True)
    candidates.add_argument("--unlock-test", metavar="REASON", help="required to run on the held-out test split")

    classify = commands.add_parser("classify", parents=[shared], help="stage 2, the model")
    classify.add_argument("--model", required=True)
    classify.add_argument("--base-url", required=True)
    classify.add_argument("--prompt", choices=sorted(CLASSIFICATION_PROMPTS), default="v1")
    classify.add_argument("--mode", choices=("legacy", "cascade"), default="cascade")
    classify.add_argument("--passes", type=int, default=5, help="votes per pair in legacy mode")
    classify.add_argument("--predictions", required=True, help="directory of resumable prediction files")
    classify.add_argument("--out", help="result file (not needed with --time-first)")
    classify.add_argument("--limit", type=int, help="classify only this many pairs, drawn by seeded shuffle")
    classify.add_argument("--time-first", type=int, metavar="N", help="time N pairs, project the total, write nothing")
    classify.add_argument("--api-key-env", default="OPENAI_COMPAT_API_KEY")
    classify.add_argument("--unlock-test", metavar="REASON", help="required to run on the held-out test split")
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "candidates":
        try:
            report = run_candidates(args.bench, args.out, seed=args.seed, unlock_test=args.unlock_test)
        except TestSplitLockedError as error:
            print(f"refused: {error}", file=sys.stderr)
            return 2
        print(candidate_summary(report))
        return 0
    if args.out is None and args.time_first is None:
        parser.error("--out is required unless --time-first is given")
    try:
        # "local" is what a local Ollama accepts when no key is set.
        llm = make_service(args.model, args.base_url, os.environ.get(args.api_key_env) or "local")
        report = run_classify(
            args.bench, llm, model=args.model, prompt=args.prompt, mode=args.mode, passes=args.passes,
            predictions_dir=args.predictions, out_path=args.out, seed=args.seed, limit=args.limit,
            time_first=args.time_first, unlock_test=args.unlock_test, base_url=args.base_url,
        )
    except (TestSplitLockedError, PredictionsMismatchError) as error:
        print(f"refused: {error}", file=sys.stderr)
        return 2
    if report is not None:
        print(classify_summary(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
