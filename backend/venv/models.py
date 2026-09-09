from pydantic import BaseModel
from datetime import datetime

class Applicant(BaseModel):
    name: str
    age: int
    date_of_birth: datetime
    residence: str
    skill_of_interest: str
    motivation: str
    goal_after_training: str

class InterviewAnswer(BaseModel):
    applicant_id: str
    answers: str


class SelectionRequest(BaseModel):
    seats: int = 5


class claim(BaseModel):
    claim: str
    evidence: str | None = None
    evidence_strength: str = 'unsupported'