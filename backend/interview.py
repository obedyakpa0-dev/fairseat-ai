"""Interview state management with full chat transcript tracking."""

FOUNDATION_QUESTIONS = [
    "Can you tell us about yourself?",
    "Why do you want to join this training program?",
    "What skill are you hoping to acquire or improve through this training?",
    "Can you describe a challenging situation you've faced and how you handled it?",
]

MIN_FOLLOW_UPS = 2

# In-memory store: applicant_id -> interview dict
interviews: dict = {}


def create_interview() -> dict:
    return {
        "question_index": 0,
        "answers": [],              # raw answer strings
        "transcript": [],           # list of {"role": str, "content": str}
        "follow_up_count": 0,
        "follow_up_questions": [],
        "evidence_flags": {},       # filled by ai.evidence_assessment
        "complete": False,
    }


def next_question(interview: dict) -> str | None:
    idx = interview["question_index"]
    if idx < len(FOUNDATION_QUESTIONS):
        return FOUNDATION_QUESTIONS[idx]
    follow_up_idx = interview["follow_up_count"]
    if follow_up_idx < MIN_FOLLOW_UPS:
        questions = interview.get("follow_up_questions", [])
        if follow_up_idx < len(questions):
            return questions[follow_up_idx]
    interview["complete"] = True
    return None
