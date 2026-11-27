#!/usr/bin/env python3
"""CLI: Suite B resolution benchmark (B0 vs B1)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.suite_b import SuiteBConfig, run_suite_b


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Suite B correction-pair benchmark")
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument(
        "--pairs",
        type=Path,
        default=Path("data/processed/correction_pairs.csv"),
    )
    parser.add_argument(
        "--splits",
        type=Path,
        default=Path("data/evaluation/splits.json"),
    )
    parser.add_argument(
        "--split",
        choices=("train", "tune", "test", "all"),
        default="test",
        help="Year hold-out split (default: test=2025)",
    )
    parser.add_argument(
        "--ranker",
        choices=("b0", "b1", "b2", "b3", "b4", "b5", "all", "both", "lexical", "hybrid", "graph"),
        default="both",
        help="all=b0–b4+b5, hybrid=b5, lexical=b2+b3, graph=b4, both=b0+b1",
    )
    parser.add_argument(
        "--embedding-backend",
        choices=("fastembed", "hashing"),
        default="fastembed",
        help="B3 encoder (hashing for CI smoke only)",
    )
    parser.add_argument(
        "--embedding-cache-dir",
        type=Path,
        default=Path("data/evaluation"),
    )
    parser.add_argument("--max-pairs", type=int, default=None)
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Write JSON results (default: stdout only)",
    )
    args = parser.parse_args()

    config = SuiteBConfig(
        raw_dir=args.raw_dir,
        pairs_path=args.pairs,
        splits_path=args.splits if args.splits.is_file() else None,
        split=args.split,
        max_pairs=args.max_pairs,
        embedding_backend=args.embedding_backend,
        embedding_cache_dir=args.embedding_cache_dir,
    )

    results = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "config": {
            "raw_dir": str(args.raw_dir),
            "pairs": str(args.pairs),
            "split": args.split,
            "max_pairs": args.max_pairs,
        },
        "runs": [],
    }
    if args.ranker == "both":
        rankers = ("b0", "b1")
    elif args.ranker == "all":
        rankers = ("b0", "b1", "b2", "b3", "b4", "b5")
    elif args.ranker == "hybrid":
        rankers = ("b5",)
    elif args.ranker == "lexical":
        rankers = ("b2", "b3")
    elif args.ranker == "graph":
        rankers = ("b4",)
    else:
        rankers = (args.ranker,)
    for ranker in rankers:
        results["runs"].append(run_suite_b(config, ranker=ranker))

    payload = json.dumps(results, indent=2)
    print(payload)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload, encoding="utf-8")


if __name__ == "__main__":
    main()