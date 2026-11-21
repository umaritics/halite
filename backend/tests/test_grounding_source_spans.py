"""Exact source locations are display annotations, never new support judgments."""
import unittest
from investigation.grounding import check_reply, content_tokens, source_matches


class SourceSpanTests(unittest.TestCase):
    def test_repeated_words_numbers_and_non_bmp_prefix_use_browser_offsets(self):
        text = '😀 Pump pump 3.5 psi AALA2024010100001.'
        result = source_matches(text, {'pump', '3.5', 'psi', 'aala', '2024010100001'})
        self.assertEqual(result, {'version': 'content-token-spans-v1', 'encoding': 'utf-16', 'spans': [
            {'start': 3, 'end': 7, 'token': 'pump'}, {'start': 8, 'end': 12, 'token': 'pump'},
            {'start': 13, 'end': 16, 'token': '3.5'}, {'start': 17, 'end': 20, 'token': 'psi'},
        ]})

    def test_stopwords_ids_and_absent_terms_are_not_highlighted(self):
        text = 'The pump was not leaking. AALA2024010100001.'
        result = source_matches(text, content_tokens('The pump is not cracked AALA2024010100001.'))
        self.assertEqual([s['token'] for s in result['spans']], ['pump', 'not'])
        self.assertEqual(source_matches('', {'pump'})['spans'], [])

    def test_audit_keeps_unrated_score_and_exact_source_while_adding_matches(self):
        rid = 'AALA2024010100001'
        text = '😀 No pump leak; pump checked.'
        result = check_reply(f'No pump leak {rid}.', [{'record_id': rid, 'text': text, 'part_name': 'PUMP'}])
        item = result['sentences'][0]
        self.assertEqual(item['level'], 'unrated')
        self.assertEqual(item['score'], 1)
        self.assertEqual([s['token'] for s in item['candidates'][0]['source_matches']['spans']], ['no', 'pump', 'leak', 'pump'])
        self.assertEqual(text, '😀 No pump leak; pump checked.')

    def test_source_metadata_does_not_create_nonexistent_narrative_matches(self):
        rid = 'AALA2024010100001'
        result = check_reply(f'Pump {rid}.', [{'record_id': rid, 'text': 'Inspected valve.', 'part_name': 'PUMP'}])
        self.assertEqual(result['sentences'][0]['candidates'][0]['source_matches']['spans'], [])
        self.assertEqual(result['sentences'][0]['score'], 1)


if __name__ == '__main__':
    unittest.main()
