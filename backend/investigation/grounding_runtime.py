"""Attach saved sentence audits without changing existing explanation fields."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from fastapi import HTTPException

from investigation.grounding import GroundingParameters, check_reply

_UNSET=object()


def load_configuration(settings):
    path=getattr(settings,'SESSION_GROUNDING_FILE','') if settings is not None else ''
    if not path:return None
    try:
        raw=Path(path).read_bytes()
        data=json.loads(raw)
        if data.get('status') not in ('experimental','selected'):
            raise ValueError('Explicit experimental/selected status required.')
        if data['status']=='selected' and not (data.get('label_result_sha256') and data.get('decision_reference')):
            raise ValueError('Selected thresholds require human-label and decision evidence.')
        parameters=GroundingParameters(**data['parameters'])
        return parameters,{'file_sha256':hashlib.sha256(raw).hexdigest(),'status':data['status'],
                            'label_result_sha256':data.get('label_result_sha256'),'decision_reference':data.get('decision_reference')}
    except (OSError,ValueError,KeyError,TypeError) as exc:
        raise HTTPException(503,'Sentence-check settings are invalid; no validated rating was fabricated.') from exc


def annotate(text,evidence,settings=None,*,structured_answer=False,configuration=_UNSET):
    config=load_configuration(settings) if configuration is _UNSET else configuration
    parameters,provenance=config if config else (None,None)
    # Structured answers preserve the graph/model-independent snapshot boundary.
    # Current selected lexical configurations need no encoder at all.
    embedder=(lambda texts:None) if structured_answer else None
    result=check_reply(text or '',evidence,parameters=parameters,embedder=embedder)
    if parameters and parameters.lexical_weight<1 and result['checked_with']=='lexical':
        # A blended-mode threshold cannot be silently reused as validated lexical
        # calibration after an encoder outage. Keep the scores; withhold ratings.
        for sentence in result['sentences']:
            if sentence['citations'] and not sentence['invalid_citations']:
                sentence.update(level='unrated',reason='Dense configuration unavailable; lexical fallback thresholds need validation.')
        result['status']='fallback_thresholds_pending'
        result['unsupported_count']=sum(s['level']=='unsupported' for s in result['sentences'])
    result['configuration']=provenance
    result['evidence']=deepcopy(evidence)
    return result


def annotate_response(response,settings=None,*,structured_answer=False,configuration=_UNSET):
    evidence = response['evidence']
    context = response.get('prose_context')
    if context and context.get('accepted_as_reply'):
        allowed = set(context['evidence_record_ids'])
        evidence = [record for record in evidence if record['record_id'] in allowed]
    response['grounding']=annotate(response.get('reply') or '',evidence,settings,structured_answer=structured_answer,configuration=configuration)
    return response


def annotate_diagnose(response,context,ranked,settings,*,configuration=_UNSET):
    # L2 mirrors the exact bounded prompt ID lists. Full source narratives are
    # retained in this additive audit, without changing frozen evidence fields.
    allowed={str(r['record_id']) for r in [*context.get('asset_history',[])[:5],*context.get('fleet_matches',[])[:5]]}
    allowed.update(rid for item in ranked[:5] for rid in item.get('evidence_record_ids',[])[:3])
    if response.get('llm_status')=='unavailable':
        # Deterministic fallback receives the complete collected evidence list,
        # not the bounded LLM prompt. Its shown source boundary is that list.
        allowed={str(r['record_id']) for r in response.get('evidence',[])}
    by_id={str(r['record_id']):r for r in [*context.get('asset_history',[]),*context.get('fleet_matches',[])] if str(r['record_id']) in allowed}
    sources=[{'record_id':rid,'part_name':r.get('part_name',''),'text':r.get('text',''),
              'is_superseded':r.get('is_superseded',False)} for rid,r in by_id.items()]
    response={**response,'grounding':annotate(response.get('explanation') or response.get('fallback_explanation') or '',sources,settings,configuration=configuration)}
    return response
