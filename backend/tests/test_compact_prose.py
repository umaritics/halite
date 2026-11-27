"""Real size bounds and source identity are more important than prompt wording."""
import importlib.util
import json
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location('compact_prose', Path(__file__).resolve().parents[1] / 'investigation/prose.py')
prose = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(prose)


class CompactProseTests(unittest.TestCase):
    def records(self):
        return [{'record_id': f'FAA20250000{i:02d}', 'part_name': 'HYDRAULIC PUMP', 'asset_id': f'N-TEST-{i}',
                 'status': 'superseded' if i == 0 else 'active', 'occurred_at': '2025-01-01',
                 'text': 'Pressure dropped; seal leak reported. 😀 "Quoted source". ' * 100} for i in range(20)]

    def test_twenty_saved_sources_are_unchanged_and_supplied_subset_fits_with_unicode(self):
        records = self.records()
        original = json.dumps(records, ensure_ascii=False)
        prompt, metadata = prose.build_reply_prompt(message='A' * 4000,
            ranked=[{'part_name': 'HYDRAULIC PUMP'}], delta={}, evidence=records, report_mode=True)
        self.assertLessEqual(len(prompt.encode('utf-8')), 2048)
        self.assertEqual(metadata['available_evidence_record_ids'], [r['record_id'] for r in records])
        self.assertEqual(metadata['evidence_record_ids'], [r['record_id'] for r in records[:3]])
        data = json.loads(prompt.split('\nDATA: ', 1)[1])
        self.assertEqual([r[0] for r in data['evidence']], metadata['evidence_record_ids'])
        self.assertEqual([r[1] for r in data['evidence']], [r['asset_id'] for r in records[:3]])
        self.assertTrue(data['evidence'][0][5])
        self.assertFalse(data['evidence'][1][5])
        self.assertEqual(json.dumps(records, ensure_ascii=False), original)
        self.assertEqual(metadata['max_output_tokens'], 192)
        self.assertIn('Records state', prompt)
        self.assertEqual(len(metadata['excerpted_record_ids']), 3)

    def test_short_evidence_is_not_unnecessarily_truncated_and_build_is_deterministic(self):
        args = {'message': 'pressure loss', 'ranked': [], 'delta': {},
                'evidence': [{'record_id': 'FAA2025000001', 'text': 'Pump leaked.'}]}
        self.assertEqual(prose.build_reply_prompt(**args), prose.build_reply_prompt(**args))
        prompt, metadata = prose.build_reply_prompt(**args)
        self.assertIn('Pump leaked.', prompt)
        self.assertEqual(metadata['excerpted_record_ids'], [])

    def test_duplicate_ids_and_oversized_identity_metadata_fail_explicitly(self):
        for records in [[{'record_id': 'SAME'}, {'record_id': 'SAME'}], [{'record_id': 'X' * 5000}]]:
            with self.subTest(records=len(records)), self.assertRaises(ValueError):
                prose.build_reply_prompt(message='', ranked=[], delta={}, evidence=records)

    def test_server_decision_is_passed_without_model_selection(self):
        decision = {'decision': 'abstain', 'decision_reason': 'Thin evidence'}
        prompt, _ = prose.build_reply_prompt(message='', ranked=[], delta={}, evidence=[], decision=decision)
        self.assertEqual(json.loads(prompt.split('\nDATA: ', 1)[1])['server_decision'], decision)
        self.assertIn('do not change it', prompt)

    def test_active_sources_cover_top_ranked_parts_before_historical_records(self):
        records = self.records()
        ranked = [{'part_name': 'A', 'evidence_record_ids': [records[0]['record_id'], records[8]['record_id']]},
                  {'part_name': 'B', 'evidence_record_ids': [records[9]['record_id']]}]
        _, metadata = prose.build_reply_prompt(message='', ranked=ranked, delta={}, evidence=records)
        self.assertEqual(metadata['evidence_record_ids'][:2], [records[8]['record_id'], records[9]['record_id']])
        self.assertNotIn(records[0]['record_id'], metadata['evidence_record_ids'])


if __name__ == '__main__':
    unittest.main()
