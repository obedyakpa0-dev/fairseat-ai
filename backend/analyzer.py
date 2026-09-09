"""Assess interview answers for evidence via the Gemini LLM."""

from ai import evidence_assessment


def analyze_answers(answers: list[str]) -> dict[str, bool]:
    """Return five boolean evidence flags for the given answers.

    Keys: specific_example, personal_action, outcome, reflection, plan.
    Propagates LLMError so callers can surface the failure to the client.
    """
    flags, _ = evidence_assessment(answers)
    return flags
