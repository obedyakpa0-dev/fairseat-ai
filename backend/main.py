"""Fairseat AI — FastAPI application entry point."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from models import Applicant, InterviewAnswer, SelectionRequest
from interview import create_interview, interviews, next_question, FOUNDATION_QUESTIONS
from followup import generate_follow_up_questions
from analyzer import analyze_answers
from selection import rank_applicants
from ai import acknowledgement, evidence_summary, LLMError

app = FastAPI(
    title="Fairseat AI",
    description="An evidence-led placement prototype. Age, residence, and protected characteristics are never scored.",
    version="2.0.0",
)

# Static frontend
_static = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_static):
    app.mount("/static", StaticFiles(directory=_static), name="static")

# In-memory applicant registry
applicants: dict = {}


# ── health ────────────────────────────────────────────────────────────────────

@app.get("/")
def home():
    return {"message": "Fairseat AI is running"}


# ── applicants ────────────────────────────────────────────────────────────────

@app.post("/applicant")
def create_applicant(applicant: Applicant):
    applicants[applicant.name] = applicant.model_dump()
    return {
        "message": "Applicant received",
        "applicant_id": applicant.name,
        "applicant": applicant,
    }


# ── interviews ────────────────────────────────────────────────────────────────

@app.get("/interviews/{applicant_id}/start")
def start_interview(applicant_id: str):
    """Return the current question and full transcript for an applicant.

    Creates a new interview if one does not exist, so applicants can safely
    reload the page without losing their progress.
    """
    if applicant_id not in interviews:
        interviews[applicant_id] = create_interview()
    interview = interviews[applicant_id]
    question = next_question(interview)
    return {
        "applicant_id": applicant_id,
        "question": question,
        "transcript": interview["transcript"],
        "complete": interview["complete"],
    }


@app.post("/interviews/answers")
def submit_answer(data: InterviewAnswer):
    """Accept one answer, return an LLM acknowledgement and the next question."""
    interview = interviews.get(data.applicant_id)
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found. Call /interviews/{id}/start first.")

    if interview["complete"]:
        return {"message": "Interview already complete", "complete": True}

    # Append the applicant's answer to the transcript
    interview["transcript"].append({"role": "user", "content": data.answers})
    interview["answers"].append(data.answers)

    # ── LLM acknowledgement ───────────────────────────────────────────────────
    try:
        ack, _ = acknowledgement(interview["transcript"])
    except LLMError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    interview["transcript"].append({"role": "assistant", "content": ack})

    # ── Advance state ─────────────────────────────────────────────────────────
    in_foundation = interview["question_index"] < len(FOUNDATION_QUESTIONS)

    if in_foundation:
        interview["question_index"] += 1
        # When foundation questions are done, generate LLM follow-ups
        if interview["question_index"] == len(FOUNDATION_QUESTIONS):
            try:
                interview["follow_up_questions"] = generate_follow_up_questions(interview["answers"])
            except LLMError as exc:
                raise HTTPException(status_code=503, detail=str(exc))
    else:
        interview["follow_up_count"] += 1

    # ── Evidence assessment once all questions are answered ───────────────────
    question = next_question(interview)
    if interview["complete"]:
        try:
            interview["evidence_flags"] = analyze_answers(interview["answers"])
        except LLMError as exc:
            raise HTTPException(status_code=503, detail=str(exc))

    return {
        "message": "Answer submitted",
        "applicant_id": data.applicant_id,
        "acknowledgement": ack,
        "next_question": question,
        "transcript": interview["transcript"],
        "complete": interview["complete"],
    }


# ── selection ─────────────────────────────────────────────────────────────────

@app.post("/selection")
def selection(data: SelectionRequest):
    """Rank applicants and return placements.

    Scores are derived only from the five boolean evidence flags set by the
    LLM assessor. Age, residence, and all other protected attributes are
    absent from the scoring function.
    """
    ranked = rank_applicants(applicants, interviews, data.seats)

    # Attach LLM-generated evidence summaries for completed applicants
    for entry in ranked:
        aid = entry["applicant_id"]
        iv = interviews.get(aid, {})
        if iv.get("complete") and iv.get("answers"):
            try:
                summary, _ = evidence_summary(iv["answers"], "")
                entry["evidence_summary"] = summary
            except LLMError:
                entry["evidence_summary"] = None

    return {
        "seats": data.seats,
        "placements": ranked[: data.seats],
        "non_placements": ranked[data.seats :],
    }
