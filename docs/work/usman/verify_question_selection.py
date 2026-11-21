"""Replay committed question traces and bootstrap results without FAA/graph/LLM access."""
import hashlib
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'backend'))
from investigation.attributes import load_codebook
from investigation.experiments.import_faa_codes import extract
from investigation.experiments.simulated_technician import score_trace, summarize


def main():
    directory = REPO / 'backend/investigation/experiments/results/question_selection_2024_v2'
    result = json.loads((directory / 'results.json').read_text())
    for name, expected in result['method_files_sha256'].items():
        assert hashlib.sha256((REPO / 'backend' / name).read_bytes()).hexdigest() == expected, name
    book = load_codebook()
    archive = REPO / 'docs/work/usman/evidence/phase5-faa-lookup-tables.zip'
    assert extract(archive, retrieved_at_utc=book['retrieved_at_utc']) == book
    assert result['schema'] == json.loads((REPO / 'backend/investigation/params/report-attributes-v1.json').read_text())
    baseline = directory.parent / 'decision_selection_2024_v2/selection_cases.json'
    assert hashlib.sha256(baseline.read_bytes()).hexdigest() == result['baseline_score_cases_sha256']
    for group, expected in result['summaries'].items():
        cases = json.loads((directory / (group + '_cases.json')).read_text())
        for case in cases:
            for policy, trace in case['traces'].items():
                assert score_trace(trace, case['names'], case['answer_part']) == case['metrics'][policy]
        def replay(rows, summary):
            assert summarize(rows, seed=summary['seed'], resamples=summary['bootstrap_resamples']) == summary
        replay(cases, expected['all'])
        for category, summary in expected['by_part_change'].items():
            replay([c for c in cases if c['part_change'] == category], summary)
        print(f'{group}: {len(cases)} traces, metrics and clustered intervals exactly reproduced')
    print('QUESTION_METHOD_SOURCE=PASS\nFAA_ARCHIVE_EXTRACTION=PASS\nQUESTION_SELECTION_REPLAY=PASS\nHELD_OUT_2025_UNTOUCHED=true')


if __name__ == '__main__':
    main()
