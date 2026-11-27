"""Deterministic explanations for model outages, grounded only in shown records."""


def templated_explanation(ranked: list[dict], evidence: list[dict]) -> str:
    active_ids = {r['record_id'] for r in evidence if not r.get('is_superseded')}
    current = [r for r in ranked if active_ids.intersection(r.get('evidence_record_ids', []))]
    lines = []
    if current:
        top = current[0]
        ids = [rid for rid in top.get('evidence_record_ids', []) if rid in active_ids]
        lines.append(f"Most supported check: {top['part_name']} ({len(ids)} records: {', '.join(ids)}).")
        signals = {"asset_history": "this aircraft's service history", "fleet_match": "similar fleet reports",
                   "same_model": "reports for the same aircraft model", "fleet": "fleet reports"}
        sources = [signals[s] for s in top.get('sources', []) if s in signals]
        if sources:
            lines.append('Ranking signals: ' + ' and '.join(sources[:2]) + '.')
        lines.append('This ranking is provisional; it does not establish a fault cause.')
    else:
        ids = ', '.join(r['record_id'] for r in evidence) or 'none'
        lines.append(f'The history is too thin to rank a cause. Records found: {ids}.')
    for record in evidence:
        if record.get('is_superseded'):
            lines.append(f"Record {record['record_id']} was superseded; it is shown as history only.")
    lines.append('Language model unavailable: this text was generated from the ranking, not written by a model.')
    return '\n'.join(lines)
