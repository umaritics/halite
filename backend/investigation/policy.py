"""Auditable answer/ask/abstain rule. There is no implicit production operating point."""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class PolicyParameters:
    tau_answer: float
    g_min: float
    n_min: int = 2
    max_questions: int = 3

    def __post_init__(self):
        if not math.isfinite(self.tau_answer) or not 0 <= self.tau_answer <= 1:
            raise ValueError('tau_answer must be between zero and one.')
        if not math.isfinite(self.g_min) or self.g_min < 0:
            raise ValueError('g_min must be finite and nonnegative.')
        if type(self.n_min) is not int or self.n_min < 1:
            raise ValueError('n_min must be a positive integer.')
        if type(self.max_questions) is not int or self.max_questions < 0:
            raise ValueError('max_questions must be a nonnegative integer.')


def decide(beliefs: dict, *, parameters: PolicyParameters | None = None,
           questions_asked: int = 0, best_question: dict | None = None,
           report_mode: bool = False) -> dict:
    if type(questions_asked) is not int or questions_asked < 0:
        raise ValueError('questions_asked must be a nonnegative integer.')
    top = next(iter(beliefs.get('hypotheses', [])), None)
    b_top = float(top['belief']) if top else 0.0
    count = int(top.get('evidence_count', 0)) if top else 0
    if not math.isfinite(b_top) or not 0 <= b_top <= 1 or count < 0:
        raise ValueError('Invalid leading hypothesis.')
    gain = float(best_question['gain_bits']) if best_question else None
    if gain is not None and (not math.isfinite(gain) or gain < 0):
        raise ValueError('Question gain must be finite and nonnegative.')
    inputs = {'b_top': b_top, 'other': beliefs.get('other'), 'evidence_count': count,
              'questions_asked': questions_asked, 'best_gain': gain,
              'calibrated': beliefs.get('calibrated', False)}
    if report_mode:
        return {'decision': 'report', 'decision_reason': 'Report summary; no fault decision.',
                'policy_status': 'report', 'question': None, 'policy_inputs': inputs}
    if parameters is None:
        decision, reason = 'abstain', 'Decision policy is not configured; ranking is provisional.'
    elif top and b_top >= parameters.tau_answer and count >= parameters.n_min:
        decision, reason = 'answer', 'Leading support and active-evidence requirements are met.'
    elif best_question and questions_asked < parameters.max_questions and gain >= parameters.g_min:
        decision, reason = 'ask', 'A question meets the information-gain requirement within the budget.'
    else:
        decision, reason = 'abstain', 'Evidence or expected information gain is insufficient.'
    inputs['parameters'] = ({'tau_answer': parameters.tau_answer, 'g_min': parameters.g_min,
                             'n_min': parameters.n_min, 'max_questions': parameters.max_questions}
                            if parameters else None)
    return {'decision': decision, 'decision_reason': reason,
            'policy_status': 'configured' if parameters else 'not_configured',
            'question': best_question if decision == 'ask' else None, 'policy_inputs': inputs}
