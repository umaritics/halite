"""Bridge persisted sessions to the existing deterministic Copilot workflow."""
from investigation.explain import templated_explanation
from services.citation_validation import validate_citations


def run_turn(*, session_id, asset_id, message, case_state, graph_repo, groq_service, question_controller=None):
    # Import lazily: the legacy route stays callable independently of session storage.
    from api.routes.diagnostics import CaseState, CopilotTurnRequest, copilot_turn, _run_copilot_turn
    if question_controller is not None:
        from fastapi import HTTPException
        from investigation.live_graph import LiveGraphSnapshot
        try:
            graph_repo = LiveGraphSnapshot(graph_repo, now=question_controller.now(), asset_id=asset_id)
        except (ValueError, KeyError, TypeError) as exc:
            raise HTTPException(503, 'Cannot build a trustworthy visible graph snapshot; no turn was saved.') from exc
    runner = copilot_turn if question_controller is None else _run_copilot_turn
    result = runner(
        CopilotTurnRequest(session_id=session_id, asset_id=asset_id, message=message,
                           case_state=CaseState(**case_state)),
        graph_repo=graph_repo, groq_service=groq_service,
        **({'write_reply': False} if question_controller else {}),
    )
    if question_controller is not None:
        return question_controller.start(result, previous_state=case_state, asset_id=asset_id,
                                         message=message, graph_repo=graph_repo, groq_service=groq_service)
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
