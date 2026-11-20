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
    # The compatibility route provides uncalibrated beliefs and an explicit
    # unconfigured policy until a measured operating point is accepted.
    result.update(grounding=None)
    return result
