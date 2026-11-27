"""The investigation vertical's sole ranking boundary; no new retrieval algorithm."""
from __future__ import annotations

from importlib import import_module

from services import diagnostic_retrieval as legacy

MID_VERSION = 'mid_heuristic-v1'


def rank(graph_repo, *, asset_id=None, symptoms=(), observations=(), ruled_out=(),
         as_of=None, mode='mid_heuristic', k=10):
    if not 1 <= k <= 10:
        raise ValueError('Investigation ranking supports one to ten hypotheses.')
    warnings = []
    if mode != 'mid_heuristic':
        try:
            service = import_module('retrieval.service')
        except ModuleNotFoundError as exc:
            if exc.name not in ('retrieval', 'retrieval.service'):
                raise  # A broken installed ranker must not masquerade as an absent extension.
            warnings.append(f'Requested ranker {mode} is unavailable; using {MID_VERSION}.')
        else:
            result = service.rank(graph_repo, asset_id=asset_id, symptoms=list(symptoms),
                                  observations=list(observations), ruled_out=list(ruled_out),
                                  as_of=as_of, mode=mode, k=k)
            if not result.get('ranker_version') or not result.get('mode'):
                raise ValueError('Retrieval must report its actual mode and version.')
            if not isinstance(result.get('hypotheses'), list) or not isinstance(result.get('evidence'), list):
                raise ValueError('Malformed retrieval response.')
            return result
    if as_of is not None:
        # The old graph API has no knowledge-time contract. Offline experiments
        # pass an already-filtered store, never silently ignore a live time bound.
        raise ValueError('Historical mid_heuristic ranking requires a prefiltered graph and as_of=None.')
    state = {'symptoms': list(symptoms), 'observations': list(observations), 'ruled_out': list(ruled_out)}
    context = legacy.build_copilot_context(graph_repo, asset_id, state)
    hypotheses = legacy.rank_copilot_checks(context, state['ruled_out'])[:k]
    evidence = {}
    for record in [*context['asset_history'], *context['fleet_matches']]:
        evidence.setdefault(record['record_id'], record)
    return {'mode': 'mid_heuristic', 'ranker_version': MID_VERSION,
            'hypotheses': hypotheses, 'evidence': list(evidence.values()),
            'context_size': context['context_size'], 'context': context, 'warnings': warnings}

# Frozen compatibility endpoints keep their existing bounded context contract.
# These aliases centralise V3's imports without changing any score or evidence.
build_diagnostic_context = legacy.build_diagnostic_context
build_copilot_context = legacy.build_copilot_context
rank_diagnostic_checks = legacy.rank_diagnostic_checks
rank_copilot_checks = legacy.rank_copilot_checks
ranking_delta = legacy.ranking_delta
