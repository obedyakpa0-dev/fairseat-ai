"""Generate tailored follow-up questions via the Gemini LLM."""

from ai import tailored_followups

FALLBACK_QUESTIONS = [
    "What specific result did your previous experience produce?",
    "What would you do differently after reflecting on that experience?",
]


def generate_follow_up_questions(answers: list[str]) -> list[str]:
    """Return exactly two evidence-seeking follow-up questions.

    Calls the LLM; propagates LLMError so the caller can surface it to the
    client rather than silently replacing the model with scripted answers.
    """
    questions, _ = tailored_followups(answers, FALLBACK_QUESTIONS)
    return questions
