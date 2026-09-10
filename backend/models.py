from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator


class Applicant(BaseModel):
    """Applicant data with compatibility fields for both legacy and UI payloads."""

    model_config = ConfigDict(extra="ignore")

    name: str
    age: int | None = None
    date_of_birth: str | None = None
    residence: str | None = None
    skill: str | None = None
    skill_of_interest: str | None = None
    motivation: str
    goal: str | None = None
    goal_after_training: str | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_aliases(cls, values: Any) -> Any:
        if isinstance(values, dict):
            normalized = dict(values)
            if "skill_of_interest" not in normalized and "skill" in normalized:
                normalized["skill_of_interest"] = normalized["skill"]
            if "goal_after_training" not in normalized and "goal" in normalized:
                normalized["goal_after_training"] = normalized["goal"]
            if "residence" not in normalized and "town" in normalized:
                normalized["residence"] = normalized["town"]
            return normalized
        return values


class ChatMessage(BaseModel):
    """A single turn in the interview chat transcript."""

    role: str
    content: str


class InterviewAnswer(BaseModel):
    model_config = ConfigDict(extra="ignore")

    applicant_id: str | None = None
    answer: str | None = None
    answers: str | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_answer(cls, values: Any) -> Any:
        if isinstance(values, dict):
            normalized = dict(values)
            if "answers" not in normalized and "answer" in normalized:
                normalized["answers"] = normalized["answer"]
            return normalized
        return values


class SelectionRequest(BaseModel):
    seats: int = 5
