"""Build the citation-masked benchmark for one year.

Every announced correction ("SUPPLEMENTAL REPORT FOR (<id>)") is a free label. Hide the announcement,
then ask what staging would ask: is the earlier report among the candidates (stage 1), and would the
model call the new one a supersession (stage 2, run elsewhere)? This module only builds the pairs and
records where the true prior lands under each candidate ordering.

Run:  python -m integrity.bench.build --raw-dir <dir with SDR-<year>.csv> --year 2024 --masking M2 --out <dir>
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

from integrity.bench.corpus import Corpus, file_sha256, load_year, split_of
from integrity.bench.masking import MASKINGS, leaks, mask_text
from integrity.candidates import ORDERINGS, pair_score, rank_candidates
from integrity.citations import parse_citations
from integrity.timeutil import is_eligible_prior, is_known_not_later, submission_gap_days
from services.conflict_screen import text_overlap_features

BUILDER_VERSION = "integrity-bench-1"
DEFAULT_SEED = 20261124
CHECK_SAMPLE_SIZE = 50
_RECORD_FIELDS = (
    "record_id", "asset_key", "occurred_at", "submitted_at",
    "part_name", "part_condition", "part_location", "jasc_code", "text",
)
_REJECTION_REASONS = ("cites_itself", "cited_id_absent", "other_aircraft", "prior_submitted_later")
_CHECK_COLUMNS = (
    "new_record_id", "prior_record_id", "tail",
    "new_occurred_at", "prior_occurred_at", "new_submitted_at", "prior_submitted_at",
    "new_part_name", "prior_part_name", "new_jasc_code", "prior_jasc_code",
    "new_text", "prior_text", "is_really_a_correction",
)


class SplitLockedError(RuntimeError):
    """Raised when a build would touch the held-out test year without a stated reason."""


def _source_files(raw_dir: Path, year: int) -> list[tuple[int, Path]]:
    """The file of this year and of every earlier year present; later years are never read."""
    found = {}
    for path in sorted(raw_dir.iterdir()):
        match = re.fullmatch(r"SDR-(\d{4})\.csv(?:\.gz)?", path.name)
        if match and int(match.group(1)) <= year:
            found.setdefault(int(match.group(1)), path)
    if year not in found:
        raise FileNotFoundError(f"no SDR-{year}.csv in {raw_dir}")
    return sorted(found.items())


def _rejection(corpus: Corpus, new: dict, cited: str) -> str | None:
    """Why a cited id is not a usable label, or None when it is."""
    if cited == new["record_id"]:
        return "cites_itself"
    prior = corpus.by_id.get(cited)
    if prior is None:
        return "cited_id_absent"
    if prior["asset_key"] != new["asset_key"]:
        return "other_aircraft"
    if not is_known_not_later(new, prior):
        return "prior_submitted_later"
    return None


def _rank_of(candidates: list[dict], prior_id: str, skip=frozenset()) -> int | None:
    """1-based place of prior_id, not counting the ids in skip; None when it is not a candidate."""
    place = 0
    for candidate in candidates:
        candidate_id = candidate["record"]["record_id"]
        if candidate_id in skip:
            continue
        place += 1
        if candidate_id == prior_id:
            return place
    return None


# Corrections the citation parser cannot read ("FOR SDR <id>", "SUPPLEMENATAL", "ORIGINAL REPORT WAS <id>")
# would sit in the presumed-negative pool with the answer written in them.
_UNPARSED_CORRECTION = re.compile(r"SU\w*PLE\w*\W+REP|ORIGINAL\s+REPORT", re.IGNORECASE)
_TOKEN = re.compile(r"[A-Za-z0-9]+")


def _tokens(text: str) -> set[str]:
    return {t.upper() for t in _TOKEN.findall(text or "")}


def operator_of(record_id: str) -> str:
    """The airline code the FAA ids start with; the benchmark's positives all come from one of them."""
    return record_id[:4].upper()


def operator_quotas(mix: Counter, wanted: int) -> dict[str, int]:
    """Split `wanted` across operators in proportion to mix, largest remainder first, ties by name."""
    total = sum(mix.values())
    if not total:
        return {}
    quotas = {op: wanted * n // total for op, n in mix.items()}
    by_remainder = sorted(mix, key=lambda op: (-(wanted * mix[op] % total), op))
    for op in by_remainder[: wanted - sum(quotas.values())]:
        quotas[op] += 1
    return quotas


class _Builder:
    def __init__(self, corpus: Corpus, year: int, masking: str, history_limit: int):
        self.corpus, self.year, self.masking = corpus, year, masking
        self.split = split_of(year)
        self.history_limit = history_limit
        self._masked: dict[tuple, dict] = {}
        self.dropped_related_hard_negatives = 0
        self.skipped_related_presumed = 0

    def masked(self, record: dict, extra_ids: tuple) -> dict:
        """Masked copy of a record. Its own id goes too: AA copies work-order ids into texts, for every kind alike."""
        ids = tuple(sorted({*extra_ids, record["record_id"]}))
        key = (record["record_id"], ids)
        if key not in self._masked:
            self._masked[key] = {**record, "text": mask_text(record["text"], self.masking, ids)}
        return self._masked[key]

    def related(self, new: dict, other: dict, cited: tuple) -> bool:
        """True when the raw texts name each other, or name the id the new report cites.

        Such a report (a resubmission of the same original, a duplicate) is a near-copy that a correct
        'supersedes' would be scored against, so it is neither a fair negative nor a fair prior.
        """
        return (
            other["record_id"] in _tokens(new["text"])
            or new["record_id"] in _tokens(other["text"])
            or not _tokens(other["text"]).isdisjoint(cited)
        )

    def masked_history(self, tail: str, extra_ids: tuple) -> list[dict]:
        return [self.masked(r, extra_ids) for r in self.corpus.history(tail)]

    def rank_all(self, new_m: dict, history_m: list[dict]) -> dict:
        return {o: rank_candidates(new_m, history_m, ordering=o) for o in ORDERINGS}

    def row(self, kind: str, new_m: dict, prior_m: dict, extra_ids: tuple, **fields) -> dict:
        row = {
            "pair_id": f"{new_m['record_id']}|{prior_m['record_id']}",
            "kind": kind,
            "label": 1 if kind == "positive" else 0,
            "year": self.year,
            "split": self.split,
            "masking": self.masking,
            "new": {k: new_m[k] for k in _RECORD_FIELDS},
            "prior": {k: prior_m[k] for k in _RECORD_FIELDS},
            "submission_gap_days": submission_gap_days(new_m, prior_m),
            "ranks": None, "ranks_ignoring_chain": None, "ranks_capped": None,
            "not_candidate_reason": None, "rank": None,
            "screen": text_overlap_features(new_m, prior_m),
            **fields,
        }
        for side in ("new", "prior"):
            found = leaks(row[side]["text"], self.masking, (*extra_ids, row[side]["record_id"]))
            if found:
                raise ValueError(f"{row['pair_id']}: masked {side} text still leaks {found}")
        return row

    def positives_of(self, new: dict, priors: list[dict], hard_per_positive: int) -> tuple[list[dict], int]:
        """Positive rows for one new report, each followed by its hard negatives; and how many the cap hides."""
        cited = tuple(sorted(parse_citations(new["text"])))
        new_m = self.masked(new, cited)
        history_m = self.masked_history(new["asset_key"], cited)
        ranked = self.rank_all(new_m, history_m)
        capped_history = history_m[: self.history_limit] if self.history_limit else history_m
        capped = ranked if len(capped_history) == len(history_m) else self.rank_all(new_m, capped_history)
        chain = self.corpus.chain_of(new["record_id"])
        rows, hidden = [], 0
        for prior in priors:
            prior_m = self.masked(prior, cited)
            pid = prior["record_id"]
            ranks = {o: _rank_of(ranked[o], pid) for o in ORDERINGS}
            ranks_capped = {o: _rank_of(capped[o], pid) for o in ORDERINGS}
            hidden += ranks["legacy"] is not None and ranks_capped["legacy"] is None
            reason = None
            if ranks["legacy"] is None:
                reason = "score_zero" if is_eligible_prior(new_m, prior_m) else "not_strictly_earlier"
            rows.append(self.row(
                "positive", new_m, prior_m, cited,
                ranks=ranks,
                ranks_ignoring_chain={o: _rank_of(ranked[o], pid, chain - {pid}) for o in ORDERINGS},
                ranks_capped=ranks_capped,
                not_candidate_reason=reason,
                pair_score=pair_score(new_m, prior_m),
                n_candidates=len(ranked["legacy"]),
            ))
            taken = 0
            for place, candidate in enumerate(ranked["containment"], start=1):
                if taken == hard_per_positive:
                    break
                if candidate["record"]["record_id"] in chain:
                    continue
                if self.related(new, self.corpus.by_id[candidate["record"]["record_id"]], cited):
                    self.dropped_related_hard_negatives += 1
                    continue
                taken += 1
                rows.append(self.row(
                    "hard_negative", new_m, candidate["record"], cited,
                    rank=place, pair_score=candidate["score"], n_candidates=len(ranked["legacy"]),
                ))
        return rows, hidden

    def presumed_pool(self) -> tuple[list[str], int]:
        """Ids of reports that cite nothing, are cited by nothing and have at least one candidate.

        Also returns how many were left out because they carry a correction announcement the parser misses.
        """
        pool, unparsed = [], 0
        for rid in sorted(self.corpus.by_id):
            record = self.corpus.by_id[rid]
            if record["year"] != self.year or parse_citations(record["text"]):
                continue
            if len(self.corpus.chain_of(rid)) > 1:
                continue
            if rank_candidates(record, self.corpus.history(record["asset_key"])):
                if _UNPARSED_CORRECTION.search(record["text"]):
                    unparsed += 1
                else:
                    pool.append(rid)
        return pool, unparsed

    def draw_presumed(self, pool: list[str], wanted: int, positive_operators: Counter, seed: int) -> tuple[list[tuple], int]:
        """Draw presumed negatives with the operator mix of the positives, so template style cannot predict the label.

        Where an operator has too few reports the rest comes from the whole pool; the second number says how many.
        A drawn pair whose texts name each other is skipped, as for hard negatives.
        """
        shuffled = random.Random(seed).sample(pool, len(pool))
        by_operator: dict[str, list[str]] = {}
        for rid in shuffled:
            by_operator.setdefault(operator_of(rid), []).append(rid)
        drawn, tried = [], set()

        def take(ids: list[str], count: int) -> None:
            got = 0
            for rid in ids:
                if got == count:
                    return
                if rid in tried:
                    continue
                tried.add(rid)
                new_m, top_m, ranked = self.top_candidate(rid)
                if self.related(self.corpus.by_id[rid], self.corpus.by_id[top_m["record_id"]], ()):
                    self.skipped_related_presumed += 1
                    continue
                drawn.append((rid, new_m, top_m, ranked))
                got += 1

        for operator, quota in sorted(operator_quotas(positive_operators, wanted).items()):
            take(by_operator.get(operator, []), quota)
        matched = len(drawn)
        take(shuffled, wanted - matched)
        return drawn, len(drawn) - matched

    def top_candidate(self, rid: str) -> tuple[dict, dict, dict]:
        """(masked new, masked top containment candidate, its ranking entry) for a presumed negative."""
        new_m = self.masked(self.corpus.by_id[rid], ())
        ranked = rank_candidates(new_m, self.masked_history(new_m["asset_key"], ()), ordering="containment")
        return new_m, ranked[0]["record"], ranked


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def _json_line(row: dict) -> str:
    return json.dumps(row, sort_keys=True, ensure_ascii=True) + "\n"


def _write_check_csv(path: Path, builder: _Builder, drawn: list[tuple], seed: int) -> None:
    """Fifty of the presumed negatives that are in this benchmark, unmasked, for a human to mark.

    They are a sample of the pairs the benchmark scores, so the share marked as real corrections
    estimates the label noise of exactly those pairs.
    """
    pairs = sorted((rid, top_m["record_id"]) for rid, _, top_m, _ in drawn)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(_CHECK_COLUMNS)
        for rid, prior_id in sorted(random.Random(seed).sample(pairs, min(CHECK_SAMPLE_SIZE, len(pairs)))):
            new, prior = builder.corpus.by_id[rid], builder.corpus.by_id[prior_id]
            writer.writerow([
                new["record_id"], prior["record_id"], new["asset_key"],
                new["occurred_at"], prior["occurred_at"], new["submitted_at"], prior["submitted_at"],
                new["part_name"], prior["part_name"], new["jasc_code"], prior["jasc_code"],
                new["text"], prior["text"], "",
            ])


def build(raw_dir, year: int, masking: str, out_dir, *, negatives: int | None = None,
          hard_per_positive: int = 2, history_limit: int = 200, seed: int = DEFAULT_SEED,
          unlock_test: str | None = None) -> dict:
    """Write the pair file, its manifest and the hand-check sheet; return the manifest."""
    if masking not in MASKINGS:
        raise ValueError(f"unknown masking {masking!r}; expected one of {MASKINGS}")
    split = split_of(year)
    reason = (unlock_test or "").strip()
    if split == "test" and not reason:
        raise SplitLockedError(
            f"year {year} is the held-out test split; pass --unlock-test with the reason to build it"
        )
    raw_dir, out_dir = Path(raw_dir), Path(out_dir)
    sources, records, seen = [], [], set()
    cross_file_duplicates = 0
    for file_year, path in _source_files(raw_dir, year):
        loaded, stats = load_year(path, file_year)
        for record in loaded:
            if record["record_id"] in seen:
                cross_file_duplicates += 1
                continue
            seen.add(record["record_id"])
            records.append(record)
        sources.append({"file": path.name, "year": file_year, "sha256": file_sha256(path), "load_stats": stats})

    corpus = Corpus(records)
    builder = _Builder(corpus, year, masking, history_limit)
    rejected = dict.fromkeys(_REJECTION_REASONS, 0)
    citations_found = 0
    rows, hidden_by_cap = [], 0
    for rid in sorted(corpus.by_id):
        new = corpus.by_id[rid]
        if new["year"] != year:
            continue
        priors = []
        for cited in parse_citations(new["text"]):
            citations_found += 1
            why = _rejection(corpus, new, cited)
            if why:
                rejected[why] += 1
            else:
                priors.append(corpus.by_id[cited])
        if priors:
            new_rows, hidden = builder.positives_of(new, priors, hard_per_positive)
            rows.extend(new_rows)
            hidden_by_cap += hidden

    seen_pairs, unique_rows = set(), []
    for row in rows:
        if row["pair_id"] not in seen_pairs:
            seen_pairs.add(row["pair_id"])
            unique_rows.append(row)
    rows = unique_rows
    n_positive = sum(r["kind"] == "positive" for r in rows)

    pool, pool_unparsed = builder.presumed_pool()
    wanted = n_positive if negatives is None else negatives
    positive_operators = Counter(operator_of(r["new"]["record_id"]) for r in rows if r["kind"] == "positive")
    drawn, from_other_operators = builder.draw_presumed(pool, wanted, positive_operators, seed)
    for rid, new_m, top_m, ranked in drawn:
        rows.append(builder.row(
            "presumed_negative", new_m, top_m, (),
            rank=1, pair_score=ranked[0]["score"], n_candidates=len(ranked),
        ))

    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"bench_{year}_{masking}"
    _write(out_dir / f"{stem}.jsonl", "".join(_json_line(r) for r in rows))
    _write_check_csv(out_dir / f"presumed_negatives_check_{year}_{masking}.csv", builder, drawn, seed)
    manifest = {
        "builder_version": BUILDER_VERSION,
        "year": year,
        "split": split,
        "masking": masking,
        "seed": seed,
        "options": {"negatives": negatives, "hard_per_positive": hard_per_positive, "history_limit": history_limit},
        "sources": sources,
        "cross_file_duplicates": cross_file_duplicates,
        "citations_found": citations_found,
        "rejected_citations": rejected,
        "counts": {k: sum(r["kind"] == k for r in rows) for k in ("positive", "hard_negative", "presumed_negative")},
        "presumed_negative_pool": len(pool),
        "presumed_pool_left_out_unparsed_correction": pool_unparsed,
        "presumed_negatives_from_other_operators": from_other_operators,
        "presumed_negatives_skipped_as_related": builder.skipped_related_presumed,
        "hard_negatives_dropped_as_related": builder.dropped_related_hard_negatives,
        "operator_mix": {
            kind: dict(sorted(Counter(operator_of(r["new"]["record_id"]) for r in rows if r["kind"] == kind).items()))
            for kind in ("positive", "hard_negative", "presumed_negative")
        },
        "positives_hidden_by_history_cap": hidden_by_cap,
        "unlock_test_reason": reason or None,
    }
    _write(out_dir / f"{stem}.manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--raw-dir", required=True)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--masking", choices=MASKINGS, required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--negatives", type=int, default=None, help="presumed negatives (default: number of positives)")
    parser.add_argument("--hard-per-positive", type=int, default=2)
    parser.add_argument("--history-limit", type=int, default=200, help="oldest reports kept per aircraft, as deployed; 0 means no cap")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--unlock-test", default=None, metavar="REASON", help="required to build the held-out test year")
    args = parser.parse_args(argv)
    try:
        manifest = build(
            args.raw_dir, args.year, args.masking, args.out, negatives=args.negatives,
            hard_per_positive=args.hard_per_positive, history_limit=args.history_limit,
            seed=args.seed, unlock_test=args.unlock_test,
        )
    except SplitLockedError as error:
        print(f"refused: {error}", file=sys.stderr)
        return 2
    print(json.dumps(manifest["counts"], sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
