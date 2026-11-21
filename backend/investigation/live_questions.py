"""Server-owned question snapshots. Structured answers never re-read graph/model state."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import uuid

from fastapi import HTTPException

from investigation.attributes import NOT_SURE, load_codebook, option_label
from investigation.beliefs import entropy, load_parameters, score_beliefs
from investigation.experiments.temporal_questions import known_model
from investigation.policy import PolicyParameters, decide
from investigation.questions import answer_question, build_likelihoods, select_question

ROOT = Path(__file__).parent
EXPLANATION_VERSION = 'managed-session-v1'


def visible_likelihoods(repo, names, schema, *, asset_id, message, now):
    """Read-only adaptation of the current graph; never infer missing submission times."""
    from investigation.live_graph import LiveGraphSnapshot
    snapshot = repo if isinstance(repo, LiveGraphSnapshot) else LiveGraphSnapshot(repo, now=now, asset_id=asset_id)
    now = snapshot.now
    records, corpus = snapshot.records, snapshot.corpus
    by_id = {a['id']: a for a in snapshot.assets}
    referenced = set(re.findall(r'\b[A-Z0-9]{6,}\b', message.upper())) & records.keys()
    excluded_chains = {corpus.chains[rid] for rid in referenced}
    visible = [r for rid, r in records.items() if rid in snapshot.visible_ids and corpus.chains[rid] not in excluded_chains]
    asset = by_id.get(asset_id, {})
    model = known_model(str(asset.get('make') or '').strip() + '/' + str(asset.get('model') or '').strip())
    models = build_likelihoods(visible, names, schema, aircraft_model=model)
    audit = {'knowledge_time': now.isoformat(), 'n_visible_records': len(visible),
             'invalid_or_missing_submission_time': snapshot.invalid,
             'equal_or_future_records': sum(r['submitted_at'] >= now for r in records.values()),
             'referenced_record_ids': sorted(referenced),
             'excluded_chain_record_ids': sorted(rid for rid in records if corpus.chains[rid] in excluded_chains),
             'strict_submission_bound': True, 'query_chain_excluded': True,
             'code_nonblank_counts': {key: sum(bool(r.get(key)) for r in visible) for key in
                                     ('stage_of_operation', 'how_discovered', 'nature_of_condition', 'precautionary_procedure')}}
    return models, audit


def _vector(beliefs, names):
    lookup = {h['part_name']: h['belief'] for h in beliefs['hypotheses']}
    values = [lookup[name] for name in names] + [beliefs['other']]
    entropy(values)
    return values


def _with_posterior(base, names, values):
    lookup = dict(zip(names, values))
    result = deepcopy(base)
    # Stable original-rank tie order; matrix basis stays fixed in saved state.
    result['hypotheses'] = sorted(({**h, 'belief': lookup[h['part_name']]} for h in base['hypotheses']), key=lambda h: (-h['belief'], names.index(h['part_name'])))
    result.update(other=values[-1], entropy=entropy(values))
    return result


def _template(result, *, reason):
    beliefs = result['beliefs']
    lines = []
    if beliefs['hypotheses']:
        top = beliefs['hypotheses'][0]
        allowed = {r['record_id'] for r in result['evidence'] if not r.get('is_superseded')}
        ids = [rid for rid in top.get('evidence_record_ids', []) if rid in allowed]
        if ids:
            lines.append(f"Leading historical support: {top['part_name']}. Active supporting reports: {', '.join(ids)}.")
        else:
            lines.append('The leading candidate has no active supporting narrative in this saved evidence set.')
    else:
        lines.append('No ranked candidate was found in the available history.')
    if result['decision'] == 'abstain':
        lines.append('The history is insufficient for an answer. Consult approved maintenance documentation and a qualified supervisor.')
    elif result['decision'] == 'ask':
        lines.append('The ranking is provisional. Answer the saved multiple-choice question to refine its relative support.')
    elif result['decision'] == 'report':
        lines.append('This is a record-summary request; no fault decision is made.')
    lines.append('Historical support does not establish a fault cause or approve a repair.')
    lines.append(reason)
    return '\n'.join(lines)


def _saved_citations(text, evidence):
    # Validation is against saved evidence only; graph/model changes cannot alter answer replay.
    from services.citation_validation import extract_record_id_candidates
    allowed = {r['record_id'] for r in evidence}
    ids = extract_record_id_candidates(text)
    valid, invalid = sorted(set(ids) & allowed), sorted(set(ids) - allowed)
    for rid in invalid:
        text = text.replace(rid, f'[UNVERIFIED:{rid}]')
    return text, {'valid_ids': valid, 'invalid_ids': invalid, 'all_valid': not invalid}


class QuestionController:
    def __init__(self, policy, *, now=None):
        if policy.get('selection_year') != 2024 or policy.get('status') not in ('experimental', 'selected'):
            raise ValueError('A 2024 experimental or explicitly selected policy is required.')
        self.policy = deepcopy(policy)
        self.parameters = PolicyParameters(**policy['parameters'])
        if self.parameters.n_min != 2 or self.parameters.max_questions != 3:
            raise ValueError('The live contract requires two records and a three-question budget.')
        if not policy.get('ranker_version'):
            raise ValueError('Policy ranker version is required.')
        if policy['status'] == 'selected' and not (policy.get('decision_reference') and policy.get('selection_sha256')):
            raise ValueError('Selected policy requires the decision and selection evidence references.')
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.book = load_codebook()
        self.schema = json.loads((ROOT / 'params/report-attributes-v1.json').read_text())
        if self.schema['fit_years'] != [2023] or self.schema['codebook_sha256'] != hashlib.sha256(json.dumps(self.book, sort_keys=True).encode()).hexdigest():
            raise ValueError('Attribute schema/source provenance does not match the official codebook.')

    @classmethod
    def from_settings(cls, settings):
        if settings is None or not settings.SESSION_QUESTIONS_ENABLED:
            return None
        try:
            path = Path(settings.SESSION_POLICY_FILE)
            policy = json.loads(path.read_text())
            policy['file_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
            return cls(policy)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise HTTPException(503, 'Question policy is enabled but its configuration/provenance is invalid.') from exc

    def _choose(self, response, state):
        beliefs = response['beliefs']
        values = _vector(beliefs, state['basis_names'])
        question = select_question(values, state['models'], excluded=[a['attribute'] for a in state['answers']], codebook=state['codebook'])
        policy = state['policy']
        choice = decide(beliefs, parameters=PolicyParameters(**policy['parameters']), questions_asked=len(state['answers']),
                        best_question=question, report_mode=bool(response.get('report_mode')))
        response.update(choice, policy_status=policy['status'], question_feature_enabled=True,
                        policy_provenance=deepcopy(policy), grounding=None)
        if response['question']:
            response['question']['id'] = str(uuid.uuid4())
        state['active_question'] = deepcopy(response['question'])
        response['case_state']['question_state'] = state
        return response

    def start(self, response, *, previous_state, asset_id, message, graph_repo, groq_service):
        try:
            version = response['ranker_version']
            if version != self.policy['ranker_version']:
                raise ValueError('Question policy belongs to a different ranker version.')
            params = load_parameters(ROOT / f'params/{version}.json', ranker_version=version)
            if params.corpus_sha256 != self.schema['corpus_sha256']:
                raise ValueError('Belief and attribute fit corpora differ.')
            beliefs = score_beliefs(response['ranked_checks'], ranker_version=version, parameters=params)
            names = [h['part_name'] for h in beliefs['hypotheses']]
            models, audit = visible_likelihoods(graph_repo, names, self.schema, asset_id=asset_id, message=message, now=self.now())
            answers = deepcopy(previous_state.get('question_state', {}).get('answers', []))
            values = _vector(beliefs, names)
            for answer in answers:
                if answer['value'] != NOT_SURE:
                    model = models[answer['attribute']]
                    # An earlier observation cannot be silently dropped during a new free-text turn.
                    question = {'model':model,'options':[{'value':v} for v in model['values']]}
                    values = answer_question(values, question, answer['value'])
            response['beliefs'] = _with_posterior(beliefs, names, values)
            state = {'version':'saved-questions-v1','basis_names':names,'models':models,'answers':answers,
                     'policy':self.policy,'codebook':self.book,'schema_version':self.schema['schema_version'],
                     'likelihood_audit':audit}
            self._choose(response, state)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise HTTPException(503, 'Cannot build a trustworthy question snapshot; no turn was saved.') from exc
        response['explanation_version'] = EXPLANATION_VERSION
        if response['llm_status'] != 'unavailable' and response['evidence']:
            try:
                payload = {'decision':response['decision'], 'decision_reason':response['decision_reason'],
                           'hypotheses':response['beliefs']['hypotheses'], 'other':response['beliefs']['other'],
                           'evidence':response['evidence']}
                prompt = ('Explain ONLY the saved historical evidence below. Cite exact report IDs. '
                          'The server has already selected the decision and any multiple-choice question. '
                          'Do not ask questions, choose a decision, propose tests/procedures or approve a repair. '
                          'Superseded records are history only. Relative support is not a fault probability.\n'
                          + json.dumps(payload, ensure_ascii=False))
                reply = groq_service.chat([{'role':'user','content':prompt}], max_tokens=1800,
                                          system_prompt='Write evidence-grounded prose. Never invent a fault cause or question.')
                if not reply or not str(reply).strip() or re.search(r'[?？؟]', str(reply)):
                    raise ValueError('Empty prose or an unrequested model-written question.')
                response['reply'] = str(reply).strip()
                response['explanation_source'] = 'model'
            except Exception as exc:
                response['warnings'].append(f'Model explanation rejected/unavailable: {exc}')
                response['llm_status'] = 'unavailable'
        if response['llm_status'] == 'unavailable' or not response['evidence']:
            reason = ('Language model unavailable: this text is a deterministic summary of the saved evidence.'
                      if response['llm_status'] == 'unavailable' else 'No model call is needed for an empty evidence set.')
            response['reply'] = _template(response, reason=reason)
            response['fallback_explanation'] = response['reply']
            response['explanation_source'] = 'template'
        response['reply'], response['citation_validation'] = _saved_citations(response['reply'], response['evidence'])
        return response

    def answer(self, previous_response, answer):
        if not previous_response or previous_response.get('decision') != 'ask' or not previous_response.get('question'):
            raise HTTPException(409, 'No structured question is active for this investigation.')
        question = previous_response['question']
        if answer.get('question_id') != question.get('id') or answer.get('attribute') != question['attribute']:
            raise HTTPException(409, 'The question changed. Reload the saved investigation before answering.')
        response = deepcopy(previous_response)
        state = response['case_state']['question_state']
        if state['version'] != 'saved-questions-v1' or state['active_question'] != question:
            raise HTTPException(409, 'Saved question state is inconsistent; no answer was applied.')
        prior = deepcopy(response['beliefs'])
        try:
            values = answer_question(_vector(prior, state['basis_names']), question, answer['value'])
        except (ValueError, KeyError) as exc:
            raise HTTPException(422, 'Choose an offered answer or Not sure.') from exc
        state['answers'].append({'attribute':question['attribute'],'value':answer['value'],'question_id':question['id']})
        response['beliefs'] = _with_posterior(prior, state['basis_names'], values)
        response['belief_transition'] = {'prior':prior,'posterior':deepcopy(response['beliefs']),'answer':deepcopy(answer),
                                        'basis_names':list(state['basis_names'])}
        book = state['codebook']
        label = 'Not sure' if answer['value'] == NOT_SURE else option_label(question['attribute'], answer['value'], book)
        observation = f"{question['text']} Answer recorded: {label}."
        response['case_state']['observations'] = [*response['case_state']['observations'], observation]
        self._choose(response, state)
        response.update(llm_status='not_needed', explanation_source='template', warnings=[],
                        ranking_delta={'new': [], 'moved_up': [], 'moved_down': [], 'dropped': [], 'newly_cited_records': []})
        response['reply'] = _template(response, reason='The structured answer updated saved beliefs; no language model or graph read was used.')
        response['fallback_explanation'] = response['reply']
        response['reply'], response['citation_validation'] = _saved_citations(response['reply'], response['evidence'])
        return response
