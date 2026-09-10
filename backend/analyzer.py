"""Assess interview answers for evidence via the Gemini LLM."""

try:
    from .ai import evidence_assessment
except ImportError:  # pragma: no cover - supports direct script execution.
    from ai import evidence_assessment


def analyzer_answer(answer: str):
    """Legacy helper kept for compatibility with the original challenge flow."""
    claims = []
    text = (answer or "").lower()

    if "years" in text:
        claims.append({
            "claim": "Applicant claims prior experience in the field",
            "evidence": None,
            "evidence_strength": "unsupported",
        })

    if "built" in text or "developed" in text:
        claims.append({
            "claim": "Applicant claims to have built or developed something",
            "evidence": None,
            "evidence_strength": "unsupported",
        })
    return claims


def analyze_answers(answers: list[str]) -> dict[str, bool]:
    """Return five boolean evidence flags for the given answers.

    Keys: specific_example, personal_action, outcome, reflection, plan.
    Propagates LLMError so callers can surface the failure to the client.
    """
    flags, _ = evidence_assessment(answers)
    return flags
