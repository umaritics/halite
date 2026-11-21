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
            expected = json.loads((ROOT / relative).read_text())
            if key == 'stopping_selection':
                expected['tables'] = [r for r in expected['tables'] if r['g_min'] == result['selected_policy']['parameters']['g_min']]
            self.assertEqual(result[key], expected)
        self.assertIsNone(result['decision_selection']['selection']['selected_operating_point'])
        self.assertFalse(result['question_selection']['held_out_evaluated'])
        self.assertEqual(result['publication_sha256'], hashlib.sha256((ROOT / 'publication.json').read_bytes()).hexdigest())

    def test_explicit_empty_publication(self):
        self.manifest(lambda m: m.update(artifacts=[]))
        self.assertEqual(load_results(self.root), {'schema_version': 'investigation-results-v2', 'state': 'empty', 'artifacts': []})

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

    def held_artifact(self, mutate):
        self.artifact('held_out',mutate)
        path = self.root/FILES['held_out']
        data = json.loads(path.read_text())
        self.artifact('held_out_verification',lambda v:v.update(results_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),case_counts=data['case_counts']))

    def test_backend_only_packaging_needs_no_project_document_mount(self):
        from investigation.research_results import publication_freeze
        original = publication_freeze()
        packaged = Path(self.temp.name)/'packaged_backend'
        backend_root = ROOT.parents[2]
        names = [name.removeprefix('backend/') for name in original['policy']['frozen_files_sha256'] if name.startswith('backend/')]
        names += ['investigation/params/selected-policy-v1.json', 'investigation/experiments/held_out_protocol_v1.json']
        for name in names:
            path = packaged/name;path.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(backend_root/name,path)
        self.assertEqual(publication_freeze(packaged),original)
        (packaged/'investigation/params/report-attributes-v1.json').write_text('{}')
        with self.assertRaises(ResultsUnavailable):publication_freeze(packaged)

    def test_accepted_point_is_exact_and_only_accepted_gain_rows_are_sent(self):
        result = load_results()
        policy = result['selected_policy']
        self.assertEqual(policy['parameters'], {'tau_answer':.8,'g_min':.5,'n_min':2,'max_questions':3})
        self.assertIn(policy['selected_2024_row'],result['stopping_selection']['tables'])
        self.assertEqual(len(result['stopping_selection']['tables']),756)
        self.assertTrue(all(r['g_min']==.5 for r in result['stopping_selection']['tables']))
        self.assertEqual(result['held_out']['case_counts']['n_pairs'],157)
        self.assertEqual(result['held_out_verification']['tables_verified'],72)

    def test_rehashed_selection_cannot_replace_the_frozen_choice(self):
        self.artifact('stopping_selection',lambda d:d['tables'][0].update(g_min=.123))
        with self.assertRaises(ResultsUnavailable):load_results(self.root)

    def test_rehashed_held_out_policy_change_is_rejected(self):
        self.held_artifact(lambda d:d['policy']['parameters'].update(tau_answer=.75))
        with self.assertRaises(ResultsUnavailable):load_results(self.root)

    def test_held_out_tuning_flag_is_rejected(self):
        self.held_artifact(lambda d:d.update(selection_or_tuning_performed=True))
        with self.assertRaises(ResultsUnavailable):load_results(self.root)

    def test_bad_pre_access_receipt_is_rejected(self):
        self.held_artifact(lambda d:d['pretest_receipt'].update(protocol_sha256='wrong'))
        with self.assertRaises(ResultsUnavailable):load_results(self.root)

    def test_changed_result_cannot_reuse_its_verification_receipt(self):
        self.artifact('held_out',lambda d:d['notes'].append('unverified change'))
        with self.assertRaises(ResultsUnavailable):load_results(self.root)

    def test_missing_or_duplicate_control_is_rejected(self):
        self.held_artifact(lambda d:d['stopping'].__setitem__(1,d['stopping'][0]))
        with self.assertRaises(ResultsUnavailable):load_results(self.root)

    def test_stopping_count_and_interval_validation(self):
        from investigation.research_results import stopping_metrics
        row = json.loads((ROOT/FILES['held_out']).read_text())['stopping'][0]['chosen']
        mutations = [lambda s:s.update(coverage=.123), lambda s:s.update(n_answered=-1),
                     lambda s:s.update(mean_questions=float('nan')),lambda s:s['ci95']['coverage'].update(valid_resamples=1001),
                     lambda s:s['ci95']['coverage'].update(low=1,high=0)]
        for mutate in mutations:
            copy = json.loads(json.dumps(row));mutate(copy)
            with self.subTest(row=copy), self.assertRaises(ResultsUnavailable):stopping_metrics(copy)

    def test_undefined_accuracy_remains_undefined(self):
        from investigation.research_results import stopping_metrics
        data = json.loads((ROOT/FILES['held_out']).read_text())
        row = next(t['chosen'] for t in data['stopping'] if t['cohort']=='coded_fields_only' and t['stratum']=='all' and t['strategy']=='information_gain')
        stopping_metrics(row)
        self.assertIsNone(row['accuracy_top1'])
        row['ci95']['accuracy_top1']['valid_resamples']=1000
        with self.assertRaises(ResultsUnavailable):stopping_metrics(row)

    def test_abstention_off_cannot_change_question_burden(self):
        self.held_artifact(lambda d:d['stopping'][0]['abstention_off'].update(mean_questions=2.99))
        with self.assertRaises(ResultsUnavailable):load_results(self.root)

    def test_missing_calibration_bin_and_wrong_ece_are_rejected(self):
        self.held_artifact(lambda d:d['stopping'][0]['named_top_ece']['bins'].pop())
        with self.assertRaises(ResultsUnavailable):load_results(self.root)

    def test_calibration_bin_math_is_checked(self):
        self.held_artifact(lambda d:d['stopping'][0]['named_top_ece'].update(value=.99))
        with self.assertRaises(ResultsUnavailable):load_results(self.root)

    def test_question_stopping_samples_cannot_disagree(self):
        self.held_artifact(lambda d:d['question_budget_summaries']['all_attributes']['primary_all/all'].update(n_pairs=156))
        with self.assertRaises(ResultsUnavailable):load_results(self.root)


if __name__ == '__main__':
    unittest.main()
