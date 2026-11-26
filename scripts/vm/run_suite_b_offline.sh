#!/usr/bin/env bash
# Offline Suite B on staging VM — does NOT restart halite-api or mutate Neo4j.
# Usage (on VM): ./scripts/vm/run_suite_b_offline.sh --split test --ranker all
set -euo pipefail
ROOT="${HALITE_ROOT:-/home/umar/halite}"
CORPUS="${HALITE_CORPUS:-$ROOT/corpus_data}"
IMAGE="${HALITE_EVAL_IMAGE:-halite-api:latest}"
export PYTHONUNBUFFERED=1
mkdir -p "$ROOT/logs"
exec docker run --rm --user 0:0 \
  -e PYTHONUNBUFFERED=1 \
  -v "$ROOT/backend:/app" \
  -v "$CORPUS:/app/data" \
  -w /app \
  "$IMAGE" \
  sh -c "pip install -q -r requirements-eval.txt && python evaluation/run_suite_b.py $*"