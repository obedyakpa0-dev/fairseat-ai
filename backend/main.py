"""Fairseat AI — FastAPI application entry point."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

try:
    from .models import Applicant, InterviewAnswer, SelectionRequest
    from .interview import create_interview, interviews, next_question, FOUNDATION_QUESTIONS, MIN_FOLLOW_UPS
    from .followup import generate_follow_up_questions
    from .analyzer import analyze_answers
    from .selection import rank_applicants
    from .scenario import build_scenario_applicants, scenario_rank
    from .ai import acknowledgement, evidence_summary, LLMError, enabled as llm_enabled
except ImportError:  # pragma: no cover - supports direct script execution too.
    from models import Applicant, InterviewAnswer, SelectionRequest
    from interview import create_interview, interviews, next_question, FOUNDATION_QUESTIONS, MIN_FOLLOW_UPS
    from followup import generate_follow_up_questions
    from analyzer import analyze_answers
    from selection import rank_applicants
    from scenario import build_scenario_applicants, scenario_rank
    from ai import acknowledgement, evidence_summary, LLMError, enabled as llm_enabled

app = FastAPI(
    title="Fairseat AI",
    description="An evidence-led placement prototype. Age, residence, and protected characteristics are never scored.",
    version="2.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("FRONTEND_ORIGIN", "http://127.0.0.1:3000,http://localhost:3000").split(","),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

applicants: dict[str, dict] = {}


@app.get("/")
def home():
    return {"message": "Fairseat AI API is running"}


@app.get("/api/applicants")
def list_applicants():
    result = []
    for applicant_id, payload in applicants.items():
        interview = interviews.get(applicant_id, {})
        result.append({
            "id": applicant_id,
            "name": payload.get("name", applicant_id),
            "skill": payload.get("skill") or payload.get("skill_of_interest") or "",
            "interview_complete": bool(interview.get("complete")),
        })
    return result


@app.post("/api/applicants")
def create_applicant(api_data: Applicant):
    applicant_id = api_data.name
    applicants[applicant_id] = api_data.model_dump(exclude_none=True)
    return {
        "message": "Applicant received",
        "id": applicant_id,
        "applicant_id": applicant_id,
        "applicant": applicants[applicant_id],
    }


@app.post("/applicant")
def legacy_create_applicant(applicant: Applicant):
    return create_applicant(applicant)


@app.get("/api/interviews/{applicant_id}")
def get_interview(applicant_id: str):
    interview = interviews.setdefault(applicant_id, create_interview())
    question = next_question(interview)
    return {
        "applicant_id": applicant_id,
        "question": question,
        "complete": interview["complete"],
        "messages": interview.get("transcript", []),
        "answered": len(interview.get("answers", [])),
        "total": len(FOUNDATION_QUESTIONS) + MIN_FOLLOW_UPS,
        "ai_assisted": llm_enabled(),
        "ai_available": llm_enabled(),
    }


@app.get("/interviews/{applicant_id}/start")
def legacy_start_interview(applicant_id: str):
    return get_interview(applicant_id)


@app.post("/api/interviews/{applicant_id}/reset")
def reset_interview(applicant_id: str):
    if applicant_id not in applicants:
        raise HTTPException(status_code=404, detail="Applicant not found.")
    interviews[applicant_id] = create_interview()
    return get_interview(applicant_id)


@app.post("/api/interviews/{applicant_id}/answers")
def submit_answer(applicant_id: str, payload: dict):
    interview = interviews.setdefault(applicant_id, create_interview())
    if interview.get("complete"):
        return {
            "message": "Interview already complete",
            "complete": True,
            "question": None,
            "messages": interview.get("transcript", []),
            "answered": len(interview.get("answers", [])),
            "total": len(FOUNDATION_QUESTIONS) + MIN_FOLLOW_UPS,
            "ai_assisted": llm_enabled(),
            "ai_available": llm_enabled(),
        }

    raw_answer = (payload or {}).get("answer") or (payload or {}).get("answers") or ""
    if not str(raw_answer).strip():
        raise HTTPException(status_code=400, detail="Answer is required.")

    interview["transcript"].append({"role": "user", "content": str(raw_answer)})
    interview["answers"].append(str(raw_answer))

    try:
        ack, _ = acknowledgement(interview["transcript"])
    except LLMError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    interview["transcript"].append({"role": "assistant", "content": ack})

    if interview["question_index"] < len(FOUNDATION_QUESTIONS):
        interview["question_index"] += 1
        if interview["question_index"] == len(FOUNDATION_QUESTIONS):
            try:
                interview["follow_up_questions"] = generate_follow_up_questions(interview["answers"])
            except LLMError as exc:
                raise HTTPException(status_code=503, detail=str(exc))
    else:
        interview["follow_up_count"] += 1

    question = next_question(interview)
    if interview["complete"]:
        try:
            interview["evidence_flags"] = analyze_answers(interview["answers"])
        except LLMError as exc:
            raise HTTPException(status_code=503, detail=str(exc))

    return {
        "message": "Answer submitted",
        "applicant_id": applicant_id,
        "complete": interview["complete"],
        "question": question,
        "messages": interview["transcript"],
        "answered": len(interview["answers"]),
        "total": len(FOUNDATION_QUESTIONS) + MIN_FOLLOW_UPS,
        "ai_assisted": llm_enabled(),
        "ai_available": llm_enabled(),
    }


@app.post("/interviews/answers")
def legacy_submit_answer(data: InterviewAnswer):
    if not data.applicant_id:
        raise HTTPException(status_code=400, detail="applicant_id is required.")
    payload = {"answer": data.answers or data.answer or ""}
    return submit_answer(data.applicant_id, payload)


@app.post("/api/selection")
def selection(data: SelectionRequest):
    ranked = (
        scenario_rank(applicants, interviews, len(applicants))
        if any("evidence_summary" in person for person in applicants.values())
        else rank_applicants(applicants, interviews, data.seats)
    )
    completed = [entry for entry in ranked if entry["completed_interview"]]
    placements = []
    waitlist = []
    for index, entry in enumerate(completed):
        applicant = applicants.get(entry["applicant_id"], {})
        item = {
            "id": entry["applicant_id"],
            "name": applicant.get("name", entry["applicant_id"]),
            "skill": applicant.get("skill") or applicant.get("skill_of_interest") or "",
            "reason": entry["reason"],
            "decision": "Guaranteed job" if index < 2 else "Training place",
            "guaranteed_job": index < 2,
        }
        if index < data.seats:
            placements.append(item)
        else:
            waitlist.append(item)

    if not completed:
        return {
            "assessed": 0,
            "placements": [],
            "waitlist": [],
            "note": "No completed interviews are available for review yet.",
        }

    return {
        "assessed": len(completed),
        "placements": placements[: data.seats],
        "non_placements": [
            {**item, "decision": "Waitlist" if item["decision"] == "Training place" else item["decision"]}
            for item in waitlist
        ],
        "waitlist": waitlist,
        "note": f"{len(completed)} completed interview(s) assessed. Evidence-only ranking was applied.",
    }


@app.post("/selection")
def legacy_selection(data: SelectionRequest):
    return selection(data)


@app.post("/api/demo")
def demo_seed():
    sample = build_scenario_applicants()
    for person in sample:
        applicants[person["name"]] = person
        interviews.setdefault(person["name"], create_interview())
        interviews[person["name"]]["answers"] = [person["motivation"], person["goal"]]
        interviews[person["name"]]["complete"] = True
        interviews[person["name"]]["transcript"] = [{"role": "user", "content": answer} for answer in interviews[person["name"]]["answers"]]
        interviews[person["name"]]["evidence_flags"] = {
            "specific_example": not person.get("vague_experience") and not person.get("connection"),
            "personal_action": not person.get("vague_experience") and not person.get("connection"),
            "outcome": not person.get("vague_experience") and not person.get("connection"),
            "reflection": not person.get("connection"),
            "plan": bool(person.get("goal")),
        }
    return {"message": "Challenge sample interviews loaded", "count": len(sample)}
