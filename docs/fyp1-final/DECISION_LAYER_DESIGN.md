# Decision-layer design and rationale

Status: AI-assisted draft prepared on Muhammad Usman Al Haq's behalf, at his
explicit request in this chat. It is a design proposal he can review and defend;
it is not evidence of unaided authorship, a human-labelled study or approval.
Written before implementing WP-S4. Engineering details and executed results are
linked from `docs/work/usman/WORK_LOG.md`.

The current ranker orders historical parts using heuristic scores. A high score
means strong support relative to this retrieval context; it does not mean that a
part is the aircraft's fault. I propose a separate, deterministic decision layer
so retrieval, uncertainty and the language model's explanation can be tested
independently. The model may extract observations and write prose. It cannot
choose the ranking, a question, or the decision to answer.

For at most ten ranked hypotheses, temperature-scaled softmax converts scores to
normalised beliefs. A separate “other” bucket represents a cause outside the
retrieved list. This prevents a single weak candidate receiving confidence one
merely because no alternative was retrieved. Fit temperature and the other score
by negative log likelihood, separately for each ranker version. The shared split
contract takes precedence over the guide's conflicting fit-year sentence: fit on
2023, select thresholds on 2024, and report 2025 once per method version. Before
valid fitted parameters exist, use the documented conservative fallback and say
`calibrated: false`; bars remain “relative support.” No probability wording is
introduced by this implementation.

The rule answers only when the leading named belief exceeds the selected answer
threshold and has at least two active evidence records. Otherwise it asks a
multiple-choice question if the question budget remains and measured expected
information gain reaches its selected threshold; if neither condition holds, it
abstains. An unknown policy configuration must not silently enable answers. A
report-summary request is kept distinct from a diagnostic decision. The stored
turn records the beliefs, entropy, rule inputs, parameters and ranker version so
later replay does not recompute what the system previously believed.

A plausible alternative is a threshold directly on the ranker's top score or
letting the model say how certain it is. The former ignores competing hypotheses
and changes meaning across ranker versions; the latter is hard to reproduce and
can sound confident without evidence. Softmax also has limitations: fitting on
historical correction pairs cannot prove clinical or aviation diagnostic
validity, and retrieval misses remain important. The other bucket and explicit
abstention expose those weaknesses instead of hiding them.

A wrong suggestion can direct attention to the wrong component; an extra question
mainly costs technician time. The provisional preference is therefore to avoid
unsupported answers rather than maximise answer coverage. The actual trade-off
must be visible as a 2024 accuracy–coverage table, with sample counts and bootstrap
intervals, before an operating point is selected. No numeric error-cost ratio or
successful result is invented here. On 2025 report top-1/top-3 accuracy, coverage,
unsupported top-3 suggestion rate and calibration error, with intervals and the
abstention-off baseline. Poor results remain results and require error analysis.

Question answering must use original-report fields, never the correction that
supplies the outcome label. Retrieval sees only strictly earlier submission times
and excludes the query's entire citation chain. Expected information gain is an
explicit extension after the belief/rule core; unimplemented questions cannot
manufacture an `ask` result. Sentence grounding is a separate check and will not
turn historical support into repair authority. The product remains decision
support and defers to approved maintenance documentation and qualified personnel.
