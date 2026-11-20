"""Bridge persisted sessions to the existing deterministic Copilot workflow."""
from investigation.explain import templated_explanation
from services.citation_validation import validate_citations


def run_turn(*, session_id, asset_id, message, case_state, graph_repo, groq_service):
    # Import lazily: the legacy route stays callable independently of session storage.
    from api.routes.diagnostics import CaseState, CopilotTurnRequest, copilot_turn
    result = copilot_turn(
        CopilotTurnRequest(session_id=session_id, asset_id=asset_id, message=message,
                           case_state=CaseState(**case_state)),
        graph_repo=graph_repo, groq_service=groq_service,
    )
    if result['llm_status'] == 'unavailable':
        result['fallback_explanation'] = templated_explanation(result['ranked_checks'], result['evidence'])
        result['reply'] = result['fallback_explanation']
        checked = validate_citations(result['reply'], graph_repo,
                                     allowed_ids={r['record_id'] for r in result['evidence']})
        result['reply'] = checked['flagged_text']
        result['citation_validation'] = {'valid_ids': checked['valid'], 'invalid_ids': checked['invalid'],
                                         'all_valid': not checked['invalid']}
    # Persistence can ship before a measured operating point. Never invent fitted policy decisions.
    result.update(decision='abstain', decision_reason='Decision policy is not configured; ranking is provisional.',
                  policy_status='not_configured', beliefs=None, question=None, grounding=None,
                  ranker_mode='mid_heuristic', ranker_version='mid_heuristic-v1')
    return result
