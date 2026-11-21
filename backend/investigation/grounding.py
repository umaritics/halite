"""Auditable sentence scores and citation checks; thresholds are always explicit."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import math
import re

from investigation import embed_port

VERSION = 'sentence-grounding-v1'
# Function/hedging words are not evidence. Negations and quantities are preserved.
STOP = set('a an the and or but of in on at to for from by with as this that these those it its is are was were be been being has have had do does did may might could would can should possibly probably perhaps likely reportedly apparently suggest suggests suggested seems seem based according report reports record records evidence states stated shows shown indicates indicated historical supports support supported'.split())
CONDITIONS = set('crack cracked cracking leak leaks leaking leakage broken break fractured fracture corrosion corroded worn wear damaged damage failed failure fault faulted faulty inoperative intermittent smoke vibration noise loose missing blocked clogged overheated overheating seized stuck pressure loss'.split())
NEGATIONS = {'no','not','never','without','neither','none','denied','absent'}
ABBREVIATIONS = {'e.g.','i.e.','mr.','dr.','vs.','approx.','fig.','no.'}
TOKEN = re.compile(r"[a-z]+(?:[-'][a-z]+)*|\d+(?:\.\d+)?", re.I)
# Keep the frozen legacy citation service unchanged. Grounding also recognizes
# date-shaped FAA IDs with mixed prefixes and numeric-leading FAA IDs observed
# in the actual calibration corpus (QR9R..., N6WA..., 2024FA...).
ID_TOKEN = r'(?:[A-Z]{2,6}\d{6,}|[A-Z0-9]{0,6}(?:19|20)\d{2}[A-Z0-9]{4,})'
ID = re.compile(r'\b'+ID_TOKEN+r'\b')


@dataclass(frozen=True)
class GroundingParameters:
    theta_lo: float
    theta_hi: float
    lexical_weight: float
    whitelist: tuple[str, ...] = ()
    provenance: str = ''

    def __post_init__(self):
        if any(type(v) not in (int,float) or not math.isfinite(v) for v in (self.theta_lo,self.theta_hi,self.lexical_weight)):
            raise ValueError('Finite numeric grounding parameters are required.')
        if not 0 <= self.theta_lo < self.theta_hi <= 1 or not 0 <= self.lexical_weight <= 1:
            raise ValueError('Grounding thresholds/weight are outside their valid range.')
        if not isinstance(self.whitelist,(list,tuple)) or len(self.whitelist) > 20 or any(not isinstance(s,str) or not s.strip() or len(s)>400 for s in self.whitelist):
            raise ValueError('Whitelist must contain at most twenty short exact templates.')
        if not self.provenance:
            raise ValueError('Threshold/whitelist provenance is required.')


def split_sentences(text):
    """Keep exact spans; no rewriting of negation, decimals, citations or code fences."""
    result=[]
    start=0
    for match in re.finditer(r'[.!?]+(?=[\s\]\)"\'`]|$)|\n+',text or ''):
        if match.start() < start:
            continue
        end=match.end()
        if match.group().startswith('\n'):
            piece=text[start:match.start()].strip()
        else:
            # Decimal dots cannot match the following-whitespace requirement.
            prefix=text[start:end].lower()
            last=prefix.split()[-1] if prefix.split() else ''
            if last in ABBREVIATIONS or re.search(r'\b[A-Za-z]\.$',text[start:end]):
                continue
            # A trailing citation belongs to the preceding clause: "leaked. [ID]"
            following=re.match(r'\s*\[('+ID_TOKEN+r'(?:\s*[,;]\s*'+ID_TOKEN+r')*)\]',text[end:])
            if following:
                end += following.end()
            piece=text[start:end].strip()
        if piece:
            result.append(piece)
        start=end
    if start < len(text or ''):
        piece=text[start:].strip()
        if piece:
            result.append(piece)
    return result


def content_tokens(text):
    stripped=ID.sub(' ',text or '')
    return {t.lower() for t in TOKEN.findall(stripped) if t.lower() not in STOP}



def source_matches(text, tokens):
    """Exact source-body token locations, in JavaScript UTF-16 code units.

    Display annotation only: never changes containment, guards or ratings.
    Exclude citation IDs and preserve negation, quantities and repeated words.
    """
    offsets = [0]
    for character in text:
        offsets.append(offsets[-1] + (2 if ord(character) > 0xffff else 1))
    identifiers = [(match.start(), match.end()) for match in ID.finditer(text)]
    spans = []
    for match in TOKEN.finditer(text):
        token = match.group().lower()
        if token not in tokens or any(start < match.end() and end > match.start() for start, end in identifiers):
            continue
        spans.append({'start': offsets[match.start()], 'end': offsets[match.end()], 'token': token})
    return {'version': 'content-token-spans-v1', 'encoding': 'utf-16', 'spans': spans}


def _cosine(a,b):
    if len(a)!=len(b) or not a:
        raise ValueError('Embedding dimensions do not match.')
    length_a=math.sqrt(sum(v*v for v in a));length_b=math.sqrt(sum(v*v for v in b))
    if not length_a or not length_b:
        return 0.0
    return max(0.0,min(1.0,sum(x*y for x,y in zip(a,b))/(length_a*length_b)))


def _normalize_template(text):
    # Exact text apart from whitespace and case; not broad regex/substring approval.
    return ' '.join(text.lower().split())


@lru_cache(maxsize=1)
def fitted_parts():
    data=json.loads((Path(__file__).parent/'data/grounding_parts_v1.json').read_text())
    digest=hashlib.sha256(json.dumps(data['parts'],separators=(',',':')).encode()).hexdigest()
    if data['fit_years']!=[2023] or digest!=data['parts_sha256']:
        raise ValueError('Part guard vocabulary is not the frozen 2023 fit.')
    return tuple(data['parts']),digest


def check_reply(text, evidence, *, parameters=None, embedder=None, part_vocabulary=None):
    sentences=split_sentences(text)
    by_id={str(r['record_id']):r for r in evidence}
    if len(by_id)!=len(evidence):
        raise ValueError('Grounding evidence IDs must be unique.')
    frozen,vocabulary_sha=fitted_parts() if part_vocabulary is None else (part_vocabulary,'explicit-test-or-caller-vocabulary')
    parts=({str(p).strip().lower() for p in frozen}|{str(r.get('part_name') or '').strip().lower() for r in evidence})-{''}
    part_tokens={part:frozenset(TOKEN.findall(part)) for part in parts}
    embeddings=None
    embedding_status='not_requested'
    if sentences and parameters is not None and parameters.lexical_weight < 1:
        try:
            embeddings=(embedder or embed_port.embed_texts)(sentences+[str(r.get('text') or '') for r in evidence])
            if embeddings is not None:
                if len(embeddings)!=len(sentences)+len(evidence) or not embeddings or any(not row for row in embeddings):
                    raise ValueError('Embedding result shape mismatch.')
                for row in embeddings:
                    if any(not math.isfinite(v) for v in row) or len(row)!=len(embeddings[0]):
                        raise ValueError('Malformed embedding vector.')
                embedding_status='available'
            else:
                embedding_status='unavailable'
        except Exception as exc:
            # A real optional-service failure is surfaced, never called dense success.
            embeddings=None
            embedding_status='failed:'+type(exc).__name__
    checked_with='lexical+dense' if embeddings is not None else 'lexical'
    evidence_positions={str(r['record_id']):i for i,r in enumerate(evidence)}
    whitelist={_normalize_template(s) for s in parameters.whitelist} if parameters else set()
    output=[]
    for index,sentence in enumerate(sentences):
        citations=list(dict.fromkeys(ID.findall(sentence)))
        valid=[rid for rid in citations if rid in by_id]
        invalid=[rid for rid in citations if rid not in by_id]
        tokens=content_tokens(sentence)
        candidates=[]
        for rid in valid:
            record=by_id[rid]
            report_tokens=content_tokens(str(record.get('text') or '')+' '+str(record.get('part_name') or ''))
            containment=len(tokens & report_tokens)/len(tokens) if tokens else 0.0
            dense=_cosine(embeddings[index],embeddings[len(sentences)+evidence_positions[rid]]) if embeddings is not None else None
            weight=parameters.lexical_weight if parameters and dense is not None else 1.0
            score=weight*containment+(1-weight)*(dense or 0.0)
            # Conservative lexical guards: semantic similarity cannot excuse a
            # mismatched named part/condition, quantity or explicit negation.
            missing_conditions=sorted((tokens & CONDITIONS)-report_tokens)
            mentioned_parts=sorted(part for part,words in part_tokens.items() if words and words <= tokens)
            missing_parts=[part for part in mentioned_parts if not part_tokens[part] <= report_tokens]
            numbers={t for t in tokens if t[0].isdigit()}
            missing_numbers=sorted(numbers-report_tokens)
            negation_mismatch=bool(tokens & NEGATIONS) != bool(report_tokens & NEGATIONS)
            guards={'missing_conditions':missing_conditions,'missing_parts':missing_parts,
                    'missing_numbers':missing_numbers,'negation_mismatch':negation_mismatch,
                    'empty_content':not bool(tokens)}
            candidates.append({'record_id':rid,'containment':containment,'cosine':dense,'score':score,
                               'guards':guards,'eligible_for_supported':not any(guards.values()),
                               'source_matches':source_matches(str(record.get('text') or ''),tokens & report_tokens)})
        best=max(candidates,key=lambda c:(c['score'],c['eligible_for_supported'],c['record_id'])) if candidates else None
        acceptable=False
        if not citations:
            level='uncited';reason='No report citation in this sentence.'
            acceptable=_normalize_template(sentence) in whitelist
            if acceptable:reason='Exact approved safety/hedging template.'
        elif invalid:
            level='unsupported';reason='A cited ID is absent from the saved evidence for this turn.'
        elif parameters is None:
            level='unrated';reason='Score recorded; thresholds and whitelist are not yet validated.'
        elif best is None or best['score'] < parameters.theta_lo:
            level='unsupported';reason='Support score is below the explicit lower threshold.'
        elif best['score'] >= parameters.theta_hi and best['eligible_for_supported']:
            level='supported';reason='Score and all lexical guards pass.'
        else:
            level='weak';reason='Partial score or a named-part/condition/quantity/negation guard failed.'
        output.append({'text':sentence,'citations':citations,'valid_citations':valid,'invalid_citations':invalid,
                       'level':level,'score':best['score'] if best else None,'best_record_id':best['record_id'] if best else None,
                       'acceptable_uncited':acceptable,'reason':reason,'candidates':candidates})
    return {'sentences':output,'unsupported_count':sum(s['level']=='unsupported' for s in output),
            'uncited_count':sum(s['level']=='uncited' and not s['acceptable_uncited'] for s in output),
            'checked_with':checked_with,'embedding_status':embedding_status,
            'status':'configured' if parameters else 'thresholds_pending','version':VERSION,
            'part_vocabulary_sha256':vocabulary_sha,
            'parameters':({'theta_lo':parameters.theta_lo,'theta_hi':parameters.theta_hi,'lexical_weight':parameters.lexical_weight,
                           'whitelist':list(parameters.whitelist),'provenance':parameters.provenance} if parameters else None)}
