"""Ask the model whether a new record supersedes a prior one, by majority vote.

This is the vote logic staging runs, minus its file cache, so the benchmark can call
exactly the same code on records that never touch a graph.
"""
from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import datetime, timezone

from integrity.prompts import PROMPT_VERSION, system_prompt

logger = logging.getLogger(__name__)

# Classification labels returned by the LLM
VALID_LABELS = frozenset(
    ["no_conflict", "scope_disjoint", "supersedes", "partial_supersedes", "contradicts"]
)


def parse_classification(raw: str) -> dict:
    """Parse LLM JSON response.  On failure return no_conflict with parse_failed=True."""
    text = (raw or "").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        if text.endswith("```"):
            text = text[:-3]
    try:
        data = json.loads(text)
        label = data.get("label", "no_conflict")
        if label not in VALID_LABELS:
            logger.warning("Invalid label %r from LLM, defaulting to no_conflict", label)
            label = "no_conflict"
        return {
            "label": label,
            "rationale": data.get("rationale", ""),
            "parse_failed": False,
        }
    except json.JSONDecodeError as exc:
        logger.warning("classify_conflict parse failure: %s | raw=%r", exc, text[:200])
        return {
            "label": "no_conflict",
            "rationale": "",
            "parse_failed": True,
        }


def user_prompt(new_record: dict, prior_record: dict) -> str:
    return (
        f"NEW RECORD (occurred_at={new_record.get('occurred_at', '?')}):\n"
        f"{new_record.get('text', '')[:800]}\n\n"
        f"PRIOR RECORD (occurred_at={prior_record.get('occurred_at', '?')}):\n"
        f"{prior_record.get('text', '')[:800]}"
    )


def classify_pair(
    llm,
    new_record: dict,
    prior_record: dict,
    *,
    analysis_mode: str = "legacy",
    passes: int | None = None,
    prompt_version: str = PROMPT_VERSION,
    budget_manager=None,
) -> dict:
    """Vote on one pair. Legacy asks `passes` times; cascade asks twice and three more on disagreement."""
    model = getattr(llm, "model", "test-model")
    prompt = user_prompt(new_record, prior_record)
    system = system_prompt(prompt_version)

    # Cascade starts with two votes and buys three more only if the first two do not agree.
    requested_passes = max(1, int(passes if passes is not None else 5))
    requested_passes = 2 if analysis_mode == "cascade" else requested_passes
    results = []
    totals = {key: 0 for key in (
        "prompt_tokens", "completion_tokens", "reasoning_tokens", "total_tokens"
    )}

    def run_vote() -> None:
        if budget_manager is not None:
            budget_manager.before_request(model)
        usage = {}
        try:
            if hasattr(llm, "extract_json_with_usage"):
                response = llm.extract_json_with_usage(prompt=prompt, system_prompt=system)
                raw = response["content"]
                usage = response.get("usage") or {}
            else:
                raw = llm.extract_json(prompt=prompt, system_prompt=system)
        except Exception:
            if budget_manager is not None:
                budget_manager.record_request(model, usage)
            raise
        if budget_manager is not None:
            budget_manager.record_request(model, usage)
        parsed = parse_classification(raw)
        parsed["usage"] = usage
        results.append(parsed)
        for key in totals:
            totals[key] += int(usage.get(key) or 0)

    for _ in range(requested_passes):
        run_vote()
    if analysis_mode == "cascade":
        first_labels = [r["label"] for r in results if not r.get("parse_failed")]
        if len(first_labels) != 2 or first_labels[0] != first_labels[1]:
            for _ in range(3):
                run_vote()

    # Majority vote
    labels = [r["label"] for r in results if not r.get("parse_failed")]
    if not labels:
        final_result = {"label": "no_conflict", "rationale": "", "parse_failed": True}
        top_count = 0
    else:
        best_label, top_count = Counter(labels).most_common(1)[0]
        # Find the first result with this label to get its rationale
        final_result = {
            key: value for key, value in next(
                r for r in results if r["label"] == best_label
            ).items() if key != "usage"
        }

    final_result.update({
        "method": "llm-escalated" if analysis_mode == "cascade" and len(results) == 5 else "llm",
        "model": model,
        "passes": len(results),
        "votes": results,
        **totals,
        "vote_agreement": (top_count / len(labels)) if labels else 0.0,
        "vote_split": bool(labels and top_count <= len(labels) / 2),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cache_hit": False,
        "prompt_version": prompt_version,
    })
    return final_result
