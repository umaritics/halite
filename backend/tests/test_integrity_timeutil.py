from datetime import date, timedelta

from integrity.timeutil import (
    is_eligible_prior,
    is_known_not_later,
    occurrence_gap_days,
    parse_occurred,
    parse_submitted,
    submission_gap_days,
)


def test_parse_submitted_formats():
    assert parse_submitted("2025-01-02T09:45:26.140-05:00").utcoffset() == timedelta(hours=-5)
    assert parse_submitted("2025-01-02T09:45:26Z").utcoffset() == timedelta(0)
    assert parse_submitted("2025-01-02T09:45:26").utcoffset() == timedelta(0)
    assert parse_submitted("2025-01-02").utcoffset() == timedelta(0)


def test_parse_submitted_bad_input_gives_none():
    for bad in (None, "", "   ", "not a date", 5):
        assert parse_submitted(bad) is None


def test_parse_occurred_formats():
    assert parse_occurred("2025-01-02") == date(2025, 1, 2)
    assert parse_occurred("01/02/2025") == date(2025, 1, 2)
    assert parse_occurred("") is None
    assert parse_occurred(None) is None
    assert parse_occurred("garbage") is None


def test_gaps():
    new = {"submitted_at": "2025-01-03T00:00:00Z", "occurred_at": "2025-01-01"}
    prior = {"submitted_at": "2025-01-01T12:00:00Z", "occurred_at": "2025-01-01"}
    assert submission_gap_days(new, prior) == 1.5
    assert occurrence_gap_days(new, prior) == 0
    assert submission_gap_days(new, {}) is None
    assert occurrence_gap_days({}, prior) is None


def test_offsets_decide_not_string_order():
    # As strings prior > new; as instants prior (16:00Z) is before new (20:00Z).
    prior = {"submitted_at": "2025-01-02T21:00:00+05:00"}
    new = {"submitted_at": "2025-01-02T20:00:00+00:00"}
    assert prior["submitted_at"] > new["submitted_at"]
    assert is_eligible_prior(new, prior) is True
    assert is_eligible_prior(prior, new) is False


def test_same_instant_is_not_eligible():
    a = {"submitted_at": "2025-01-02T10:00:00-05:00"}
    b = {"submitted_at": "2025-01-02T15:00:00Z"}
    assert is_eligible_prior(a, b) is False


def test_missing_submission_falls_back_to_occurrence():
    new = {"occurred_at": "2025-01-05", "submitted_at": ""}
    earlier = {"occurred_at": "2025-01-01", "submitted_at": "2025-01-02T00:00:00Z"}
    same_day = {"occurred_at": "2025-01-05"}
    assert is_eligible_prior(new, earlier) is True
    assert is_eligible_prior(new, same_day) is False


def test_unknown_on_both_counts_is_not_eligible():
    assert is_eligible_prior({}, {}) is False


def test_a_cited_report_only_has_to_be_no_later():
    stamped = {"submitted_at": "2025-01-02T10:00:00+00:00", "occurred_at": "2025-01-01"}
    undated = {"submitted_at": "", "occurred_at": "2025-01-01"}
    assert is_known_not_later(stamped, dict(stamped)) is True          # same instant
    assert is_known_not_later(undated, dict(undated)) is True          # same occurrence date
    assert is_known_not_later(stamped, {**stamped, "submitted_at": "2025-01-03T10:00:00+00:00"}) is False
    assert is_known_not_later({}, {}) is False                          # nothing known
