"""Publication integrity checks use real committed experiments, no model or DB."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from investigation.research_results import FILES, ROOT, ResultsUnavailable, load_results


class ResearchPublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'results'
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns('*.png', '*.csv'))

    def manifest(self, mutate):
        path = self.root / 'publication.json'
        data = json.loads(path.read_text())
        mutate(data)
        path.write_text(json.dumps(data))

    def artifact(self, key, mutate):
        path = self.root / FILES[key]
        data = json.loads(path.read_text())
        mutate(data)
        raw = json.dumps(data).encode()
        path.write_bytes(raw)
        def update(manifest):
            next(e for e in manifest['artifacts'] if e['id'] == key)['sha256'] = hashlib.sha256(raw).hexdigest()
        self.manifest(update)

    def test_real_publication_preserves_all_values_and_provenance(self):
        result = load_results()
        self.assertEqual(result['state'], 'available')
        for key, relative in FILES.items():
            self.assertEqual(result[key], json.loads((ROOT / relative).read_text()))
        self.assertIsNone(result['decision_selection']['selection']['selected_operating_point'])
        self.assertFalse(result['question_selection']['held_out_evaluated'])
        self.assertEqual(result['publication_sha256'], hashlib.sha256((ROOT / 'publication.json').read_bytes()).hexdigest())

    def test_explicit_empty_publication(self):
        self.manifest(lambda m: m.update(artifacts=[]))
        self.assertEqual(load_results(self.root), {'schema_version': 'investigation-results-v1', 'state': 'empty', 'artifacts': []})

    def test_missing_manifest_is_failure_not_empty(self):
        (self.root / 'publication.json').unlink()
        with self.assertRaises(ResultsUnavailable):
            load_results(self.root)

    def test_corrupt_or_modified_artifact_fails_without_substitute(self):
        for content in [b'{', b'{}']:
            (self.root / FILES['question_selection']).write_bytes(content)
            with self.assertRaises(ResultsUnavailable):
                load_results(self.root)

    def test_duplicate_or_incomplete_publication_fails(self):
        self.manifest(lambda m: m.update(artifacts=[m['artifacts'][0], m['artifacts'][0]]))
        with self.assertRaises(ResultsUnavailable):
            load_results(self.root)

    def test_arbitrary_path_and_symlink_escape_are_rejected(self):
        self.manifest(lambda m: m['artifacts'][0].update(path='../secret.json'))
        with self.assertRaises(ResultsUnavailable):
            load_results(self.root)
        shutil.copyfile(ROOT / 'publication.json', self.root / 'publication.json')
        path = self.root / FILES['question_selection']
        path.unlink()
        path.symlink_to(ROOT / FILES['question_selection'])
        with self.assertRaises(ResultsUnavailable):
            load_results(self.root)

    def test_rehashed_wrong_year_cannot_be_presented_as_selection(self):
        self.artifact('question_selection', lambda d: d.update(year=2025))
        with self.assertRaises(ResultsUnavailable):
            load_results(self.root)

    def test_rehashed_incompatible_corpus_fails(self):
        self.artifact('decision_selection', lambda d: d['selection_corpus'].update(corpus_sha256='different'))
        with self.assertRaises(ResultsUnavailable):
            load_results(self.root)

    def test_rehashed_invented_operating_point_fails(self):
        self.artifact('decision_selection', lambda d: d['selection'].update(selected_operating_point={'tau_answer': .5}))
        with self.assertRaises(ResultsUnavailable):
            load_results(self.root)

    def test_denominator_mismatch_fails(self):
        self.artifact('decision_selection', lambda d: d['selection']['curve'][0].update(coverage=.123456))
        with self.assertRaises(ResultsUnavailable):
            load_results(self.root)

    def test_nonfinite_measurement_fails(self):
        self.artifact('question_selection', lambda d: d['summaries']['all_attributes']['all']['policies']['random'][0].update(top1=float('nan')))
        with self.assertRaises(ResultsUnavailable):
            load_results(self.root)

    def test_reversed_interval_fails(self):
        self.artifact('question_selection', lambda d: d['summaries']['all_attributes']['all']['policies']['random'][0]['ci95']['top1'].update(low=1, high=0))
        with self.assertRaises(ResultsUnavailable):
            load_results(self.root)


if __name__ == '__main__':
    unittest.main()
