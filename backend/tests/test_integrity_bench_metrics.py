from integrity.bench.metrics import (
    bootstrap_interval, confusion, f1, false_link_rate, hit_rate, percentile, precision, recall,
)


def pair(label, predicted):
    return {"label": label, "predicted": predicted}


# 3 true positives, 1 false negative, 2 false positives, 4 true negatives.
PAIRS = [pair(1, True)] * 3 + [pair(1, False)] + [pair(0, True)] * 2 + [pair(0, False)] * 4


def test_confusion_and_ratios_on_a_hand_computed_example():
    assert confusion(PAIRS) == {"tp": 3, "fp": 2, "fn": 1, "tn": 4}
    assert precision(PAIRS) == 3 / 5
    assert recall(PAIRS) == 3 / 4
    assert f1(PAIRS) == 6 / 9  # 2*3 / (2*3 + 2 + 1)
    assert false_link_rate(PAIRS) == 2 / 6  # over all negatives, not over predictions


def test_every_ratio_is_none_when_its_denominator_is_zero():
    no_positives_predicted_or_true = [pair(0, False)]
    assert precision(no_positives_predicted_or_true) is None
    assert recall(no_positives_predicted_or_true) is None
    assert f1(no_positives_predicted_or_true) is None
    assert false_link_rate([pair(1, True)]) is None
    assert precision([]) is None and false_link_rate([]) is None


def test_hit_rate_counts_null_ranks_as_misses_and_k_none_as_anywhere():
    positives = [
        {"ranks": {"legacy": 1}}, {"ranks": {"legacy": 3}}, {"ranks": {"legacy": 6}}, {"ranks": {"legacy": None}},
    ]
    assert hit_rate(positives, "ranks", "legacy", 1) == 1 / 4
    assert hit_rate(positives, "ranks", "legacy", 3) == 2 / 4
    assert hit_rate(positives, "ranks", "legacy", 5) == 2 / 4
    assert hit_rate(positives, "ranks", "legacy", None) == 3 / 4
    assert hit_rate([], "ranks", "legacy", 1) is None


def test_hit_rate_reads_the_key_and_ordering_it_is_given():
    positives = [
        {"ranks": {"legacy": 2, "containment": 1}, "ranks_capped": {"legacy": None, "containment": 1}},
        {"ranks": {"legacy": 1, "containment": 1}, "ranks_capped": {"legacy": 1, "containment": None}},
    ]
    assert hit_rate(positives, "ranks", "legacy", 1) == 1 / 2
    assert hit_rate(positives, "ranks", "containment", 1) == 1.0
    assert hit_rate(positives, "ranks_capped", "legacy", None) == 1 / 2
    assert hit_rate(positives, "ranks_capped", "containment", None) == 1 / 2


def test_bootstrap_is_deterministic_for_a_seed_and_contains_the_point_estimate():
    items = [pair(1, i % 4 != 0) for i in range(40)] + [pair(0, i % 5 == 0) for i in range(40)]
    first = bootstrap_interval(items, recall, n_resamples=300, seed=7)
    assert first == bootstrap_interval(items, recall, n_resamples=300, seed=7)
    assert first != bootstrap_interval(items, recall, n_resamples=300, seed=8)
    low, high = first
    assert low <= recall(items) <= high


def test_bootstrap_of_a_constant_statistic_is_a_point_and_does_not_mutate_its_input():
    items = [1, 2, 3]
    assert bootstrap_interval(items, lambda xs: 0.5, n_resamples=50, seed=1) == (0.5, 0.5)
    assert items == [1, 2, 3]


def test_bootstrap_skips_undefined_resamples_and_gives_up_below_half():
    items = [pair(1, True)] + [pair(0, False)] * 9
    # recall is undefined whenever the single positive is not drawn (about a third of the time).
    low, high = bootstrap_interval(items, recall, n_resamples=200, seed=3)
    assert (low, high) == (1.0, 1.0)
    # an always-undefined statistic, and an empty input, have no interval
    assert bootstrap_interval(items, lambda xs: None, n_resamples=50, seed=3) == (None, None)
    assert bootstrap_interval([], recall, n_resamples=50, seed=3) == (None, None)
    # defined on only a quarter of the resamples: fewer than half, so no interval
    calls = iter(range(1000))
    assert bootstrap_interval(items, lambda xs: 1.0 if next(calls) % 4 == 0 else None, n_resamples=100, seed=3) == (None, None)


def test_percentile_is_nearest_rank():
    assert percentile([5, 1, 3, 2, 4], 0.9) == 5
    assert percentile([5, 1, 3, 2, 4], 0.5) == 3
    assert percentile([7], 0.9) == 7
