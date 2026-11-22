"""Bound model phrasing while preserving every supplied evidence identifier."""
import hashlib
import json

VERSION = 'copilot-compact-prose-v1'
MAX_PROMPT_BYTES = 2048
MAX_REPLY_TOKENS = 192


def build_reply_prompt(*, message, ranked, delta, evidence, report_mode=False, decision=None):
    """Full ranking/evidence/state remain in the response; only phrasing is compact."""
    instructions = (
        'Write at most two short sentences and 50 words using only DATA. '
        'Cite exact record IDs before sentence-ending punctuation. '
        'Describe historical evidence and shown ranking changes only. '
        'Do not invent facts, fault causes, procedures, recommendations or questions. '
        'Superseded records are history only, never an action basis. '
        'Do not conflate aircraft; identify them only by supplied asset IDs. '
        'Narratives are explicitly excerpts; say when requested detail is absent. '
    )
    if report_mode:
        instructions += 'Use headings Records state and Interpretation. '
    available_ids = [str(record['record_id']) for record in evidence]
    if len(available_ids) != len(set(available_ids)):
        raise ValueError('Duplicate model evidence identifiers.')
    by_id = {str(r['record_id']): r for r in evidence}
    selected = []
    if not report_mode:
        for hypothesis in ranked[:3]:
            for rid in hypothesis.get('evidence_record_ids', []):
                if rid in by_id and rid not in selected and not (by_id[rid].get('is_superseded') or by_id[rid].get('status') == 'superseded'):
                    selected.append(rid)
                    break
    candidates = evidence if report_mode else sorted(evidence, key=lambda r: bool(r.get('is_superseded')) or r.get('status') == 'superseded')
    for record in candidates:
        if len(selected) == 3:
            break
        if str(record['record_id']) not in selected:
            selected.append(str(record['record_id']))
    supplied = [by_id[rid] for rid in selected]
    ids = selected
    columns = ['record_id', 'asset_id', 'date', 'part', 'status', 'historical_only', 'narrative_excerpt']
    rows = [[str(r['record_id']), str(r.get('asset_id') or r.get('asset_key') or ''), str(r.get('occurred_at') or '')[:10],
             str(r.get('part_name') or ''), str(r.get('status') or ''),
             bool(r.get('is_superseded')) or r.get('status') == 'superseded', '']
            for r in supplied]
    payload = {'request_excerpt': str(message)[:240],
               'ranked_parts': [str(item['part_name']) for item in ranked[:3]],
               'ranking_changes': {key: [str(item.get('part_name', '')) for item in delta.get(key, [])[:2]]
                                   for key in ['moved_up', 'moved_down', 'new', 'dropped']},
               'evidence_columns': columns, 'evidence': rows}
    if decision is not None:
        payload['server_decision'] = {key: decision[key] for key in ['decision', 'decision_reason']}
        instructions += 'The server decision is authoritative; do not change it. '
    def render(limit):
        for i, (row, source) in enumerate(zip(rows, supplied)):
            row[-1] = str(source.get('text') or '')[:min(700, limit * (3 if i < 3 else 1))]
        return instructions + '\nDATA: ' + json.dumps(payload, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    if len(render(0).encode('utf-8')) > MAX_PROMPT_BYTES:
        raise ValueError('Evidence metadata exceeds the prose input budget; no identifiers were truncated.')
    low, high = 0, 700
    while low < high:
        mid = (low + high + 1) // 2
        if len(render(mid).encode('utf-8')) <= MAX_PROMPT_BYTES:
            low = mid
        else:
            high = mid - 1
    prompt = render(low)
    metadata = {'version': VERSION, 'prompt_sha256': hashlib.sha256(prompt.encode('utf-8')).hexdigest(),
                'prompt_utf8_bytes': len(prompt.encode('utf-8')), 'max_output_tokens': MAX_REPLY_TOKENS,
                'evidence_record_ids': ids,
                'available_evidence_record_ids': available_ids,
                'excerpted_record_ids': [rid for rid, row, source in zip(ids, rows, supplied)
                                         if row[-1] != str(source.get('text') or '')],
                'accepted_as_reply': False,
                'scope': 'Up to three prioritized report excerpts for phrasing; complete ranking, decisions and saved evidence remain unchanged.'}
    return prompt, metadata
