questions = [
    "Can you tell us about yourself?",
    "Why do you want to join this training program?",
    "What skill are you hoping to acquire or improve through this training?",
    "Can you describe a challenging situation you've faced and how you handled it?",
]

MIN_FOLLOW_UPS = 2

interviews = {}


def create_interview():
    return {
        "question_index": 0,
        "answers": [],
        "follow_up_count": 0,
        "follow_up_questions": [],
        "claims": [],
        "complete": False,
    }


def next_question(interview):
    if interview["question_index"] < len(questions):
        return questions[interview["question_index"]]
    if interview["follow_up_count"] < MIN_FOLLOW_UPS:
        return interview["follow_up_questions"][interview["follow_up_count"]]
    interview["complete"] = True
    return None


