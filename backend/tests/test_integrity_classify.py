import json

from integrity.classify import classify_pair, user_prompt
from integrity.prompts import system_prompt

NEW = {"record_id": "N", "occurred_at": "2025-01-02", "text": "n" * 900}
PRIOR = {"record_id": "P", "occurred_at": "2025-01-01", "text": "prior text"}


class FakeLLM:
    model = "fake/model"

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def extract_json(self, prompt, system_prompt=None, **_):
        self.calls.append({"prompt": prompt, "system_prompt": system_prompt})
        reply = self.replies[len(self.calls) - 1]
        return reply if reply.startswith("BAD") else json.dumps({"label": reply, "rationale": reply})


def test_user_prompt_truncates_each_text_to_800_characters():
    prompt = user_prompt(NEW, PRIOR)
    assert prompt.startswith("NEW RECORD (occurred_at=2025-01-02):\n" + "n" * 800 + "\n\n")
    assert "n" * 801 not in prompt
    assert prompt.endswith("PRIOR RECORD (occurred_at=2025-01-01):\nprior text")


def test_legacy_runs_the_requested_number_of_votes():
    llm = FakeLLM(["supersedes"] * 3)
    result = classify_pair(llm, NEW, PRIOR, passes=3)
    assert len(llm.calls) == 3
    assert result["passes"] == 3
    assert result["label"] == "supersedes"
    assert result["method"] == "llm"
    assert result["cache_hit"] is False
    assert result["prompt_version"] == "v1"


def test_cascade_stops_at_two_when_the_votes_agree():
    llm = FakeLLM(["supersedes", "supersedes"])
    result = classify_pair(llm, NEW, PRIOR, analysis_mode="cascade")
    assert len(llm.calls) == 2
    assert result["method"] == "llm"
    assert result["vote_agreement"] == 1.0


def test_cascade_escalates_to_five_on_disagreement():
    llm = FakeLLM(["supersedes", "no_conflict", "no_conflict", "supersedes", "no_conflict"])
    result = classify_pair(llm, NEW, PRIOR, analysis_mode="cascade")
    assert len(llm.calls) == 5
    assert result["method"] == "llm-escalated"
    assert result["label"] == "no_conflict"
    assert result["vote_agreement"] == 3 / 5
    assert result["vote_split"] is False


def test_all_unparseable_votes_give_parse_failed():
    llm = FakeLLM(["BAD"] * 2)
    result = classify_pair(llm, NEW, PRIOR, passes=2)
    assert result["parse_failed"] is True
    assert result["label"] == "no_conflict"
    assert result["vote_agreement"] == 0.0


def test_llm_receives_the_requested_prompt_version():
    llm = FakeLLM(["supersedes"] * 2)
    classify_pair(llm, NEW, PRIOR, passes=1, prompt_version="v2-unannounced")
    classify_pair(llm, NEW, PRIOR, passes=1)
    assert llm.calls[0]["system_prompt"] == system_prompt("v2-unannounced")
    assert llm.calls[1]["system_prompt"] == system_prompt("v1")
