from pydantic import BaseModel


class Applicant(BaseModel):
    """Applicant registration data.

    Age, date of birth, residence, and any other protected characteristics
    are intentionally absent — they must never influence scoring or placement.
    """

    name: str
    skill_of_interest: str
    motivation: str
    goal_after_training: str


class ChatMessage(BaseModel):
    """A single turn in the interview chat transcript."""

    role: str   # "user" | "assistant"
    content: str


class InterviewAnswer(BaseModel):
    applicant_id: str
    answers: str


class SelectionRequest(BaseModel):
    seats: int = 5
