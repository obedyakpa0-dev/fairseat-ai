"""Generate tailored follow-up questions via the Gemini LLM."""

try:
    from .ai import tailored_followups
except ImportError:  # pragma: no cover - supports direct script execution.
    from ai import tailored_followups

FALLBACK_QUESTIONS = [
    "What specific result did your previous experience produce?",
    "What would you do differently after reflecting on that experience?",
]


def generate_follow_up_questions(claims_or_answers):
    """Backwards-compatible helper for both claim-based and answer-based inputs."""
    if not claims_or_answers:
        return list(FALLBACK_QUESTIONS)

    if isinstance(claims_or_answers[0], dict):
        items = [
            str(item.get("claim", ""))
            for item in claims_or_answers
            if isinstance(item, dict)
        ]
    else:
        items = [str(item) for item in claims_or_answers]

    questions, _ = tailored_followups(items, FALLBACK_QUESTIONS)
    return questions
