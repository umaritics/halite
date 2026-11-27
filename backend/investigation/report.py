"""Printable closed-session report. All user/model text is escaped."""
from html import escape


def render_report(session):
    def text(value):
        return escape(str(value or '—'))
    turns = []
    for turn in session['turns']:
        response = turn['response']
        citations = ''.join(f"<li>{text(r['record_id'])}: {text(r.get('text'))}</li>"
                            for r in response.get('evidence', []))
        turns.append(f"<section><h2>Turn {turn['idx']}</h2><p>{text(turn['user_text'])}</p>"
                     f"<p>Decision: {text(response.get('decision'))}</p>"
                     f"<p class='reply'>{text(response.get('reply'))}</p><h3>Evidence</h3><ul>{citations}</ul></section>")
    return f'''<!doctype html><html lang="en"><meta charset="utf-8">
<title>Investigation {text(session['id'])}</title>
<style>body{{font:16px/1.5 system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem;color:#111;overflow-wrap:anywhere}}
h1,h2,h3{{line-height:1.2}}section{{border-top:1px solid #ccc;margin-top:2rem}}.reply{{white-space:pre-wrap}}
li{{overflow-wrap:anywhere}}@page{{size:A4;margin:16mm}}
@media print{{body{{font-size:11pt;max-width:none;margin:0;padding:0}}h1,h2,h3{{break-after:avoid}}li{{break-inside:avoid}}p{{orphans:3;widows:3}}}}</style>
<body><h1>{text(session['title'])}</h1><p>Investigation ID: {text(session['id'])}</p>
<p>Aircraft: {text(session['asset_tail'])} · Closed: {text(session['closed_at'])}</p>
<h2>Recorded outcome</h2><p>Part: {text(session['outcome_part'])} · JASC: {text(session['outcome_jasc'])}</p>
<p>{text(session['outcome_note'])}</p><p>Outcome record: {text(session['outcome_record_id'])}</p>
<p>Decision support only. Historical records and recorded findings are preserved below.</p>
{''.join(turns)}</body></html>'''
