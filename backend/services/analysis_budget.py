"""Persistent UTC-day request/token budget for maintenance conflict analysis."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


class BudgetExhausted(RuntimeError):
    def __init__(self, stopped_reason: str, budget_remaining: dict):
        super().__init__(stopped_reason)
        self.stopped_reason = stopped_reason
        self.budget_remaining = budget_remaining


class DailyBudgetManager:
    """Persist usage by UTC date and model; reserve capacity before each request."""

    def __init__(
        self,
        path: str | Path,
        *,
        request_limit: int,
        token_limit: int,
        utilization: float = 0.90,
        token_reserve: int = 1000,
        now_fn=None,
    ):
        self.path = Path(path)
        self.request_limit = request_limit
        self.token_limit = token_limit
        self.utilization = utilization
        self.token_reserve = token_reserve
        self.now_fn = now_fn or (lambda: datetime.now(timezone.utc))

    def _date(self) -> str:
        return self.now_fn().astimezone(timezone.utc).date().isoformat()

    def _load(self) -> dict:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"version": 1, "days": {}}

    def _usage(self, state: dict, model: str) -> dict:
        return state.setdefault("days", {}).setdefault(self._date(), {}).setdefault(
            "models", {}
        ).setdefault(model, {"requests": 0, "tokens": 0})

    def snapshot(self, model: str) -> dict:
        usage = self._usage(self._load(), model)
        request_cap = int(self.request_limit * self.utilization)
        token_cap = int(self.token_limit * self.utilization)
        return {
            "utc_date": self._date(),
            "model": model,
            "request_limit": self.request_limit,
            "token_limit": self.token_limit,
            "utilization": self.utilization,
            "requests_used": int(usage.get("requests", 0)),
            "tokens_used": int(usage.get("tokens", 0)),
            "requests_remaining": max(0, request_cap - int(usage.get("requests", 0))),
            "tokens_remaining": max(0, token_cap - int(usage.get("tokens", 0))),
        }

    def before_request(self, model: str) -> None:
        remaining = self.snapshot(model)
        if remaining["requests_remaining"] < 1:
            raise BudgetExhausted("daily_request_budget", remaining)
        if remaining["tokens_remaining"] < self.token_reserve:
            raise BudgetExhausted("daily_token_budget", remaining)

    def record_request(self, model: str, usage: dict | None = None) -> dict:
        state = self._load()
        counter = self._usage(state, model)
        counter["requests"] = int(counter.get("requests", 0)) + 1
        usage = usage or {}
        total = usage.get("total_tokens")
        if total is None:
            total = int(usage.get("prompt_tokens") or 0) + int(usage.get("completion_tokens") or 0)
        counter["tokens"] = int(counter.get("tokens", 0)) + int(total or 0)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(state, indent=2), encoding="utf-8")
        temporary.replace(self.path)
        return self.snapshot(model)
