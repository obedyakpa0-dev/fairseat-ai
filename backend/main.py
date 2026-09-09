from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from dotenv import load_dotenv


load_dotenv(Path(__file__).parent / ".env")
from ai import LLMError, acknowledgement, enabled as llm_enabled, evidence_assessment, evidence_summary, tailored_followups

app = FastAPI(title="Fairseat AI", version="1.0.0")
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")

applicants: dict[str, dict[str, Any]] = {}
interviews: dict[str, dict[str, Any]] = {}

CORE_QUESTIONS = [
    "What would you like to learn during this programme, and why does it matter to you now?",
    "Tell us about a time you worked through a difficult task. What did you personally do?",
    "Describe something you have made, fixed, organised, or learned. What was the outcome?",
    "If offered a place, how will you make time to complete the training and apply the skill afterwards?",
]


class ApplicantIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    age: int = Field(ge=16, le=100)
    residence: str = Field(min_length=2, max_length=120)
    skill: str = Field(min_length=2, max_length=80)
    motivation: str = Field(min_length=10, max_length=500)
    goal: str = Field(min_length=10, max_length=500)


class AnswerIn(BaseModel):
    answer: str = Field(min_length=12, max_length=2000)


class SelectionIn(BaseModel):
    seats: int = Field(default=5, ge=1, le=20)


def _new_interview() -> dict[str, Any]:
    return {
        "core_index": 0, "answers": [], "followups": [], "followup_index": 0,
        "complete": False, "ai_assisted": False,
        "messages": [{"role": "assistant", "content": CORE_QUESTIONS[0]}],
    }


def _evidence(answer: str) -> dict[str, bool]:
    text = answer.lower()
    return {
        "specific_example": any(term in text for term in ("for example", "when i", "last year", "at my", "i built", "i made", "i fixed", "i organised")),
        "personal_action": any(term in text for term in ("i did", "i made", "i built", "i created", "i solved", "i practised", "i organised", "my role")),
        "outcome": any(term in text for term in ("result", "outcome", "improved", "completed", "finished", "helped", "saved", "earned", "learned")),
        "reflection": any(term in text for term in ("learned", "would", "next time", "realised", "improve")),
        "plan": any(term in text for term in ("schedule", "evening", "weekend", "hours", "plan", "commit", "time")),
    }


def _followups(answers: list[str]) -> list[str]:
    combined = " ".join(answers)
    signals = _evidence(combined)
    prompts: list[str] = []
    if not signals["specific_example"] or not signals["personal_action"]:
        prompts.append("Please give one concrete example. What was the situation, what was your own role, and what steps did you take?")
    if not signals["outcome"]:
        prompts.append("What changed as a result? Please include a clear outcome, even if it was small or still in progress.")
    if not signals["reflection"]:
        prompts.append("Looking back, what did you learn from that experience and what would you do differently next time?")
    if not signals["plan"]:
        prompts.append("What is your realistic plan for attending the training and practising the skill each week?")
    prompts.extend([
        "What is one obstacle that could make this programme difficult, and how will you respond to it?",
        "What evidence would best show that you are ready to use this opportunity well?",
    ])
    # Every applicant gets at least two probes, even when their first answers are strong.
    return prompts[:2]


def _next_question(interview: dict[str, Any]) -> str | None:
    if interview["core_index"] < len(CORE_QUESTIONS):
        return CORE_QUESTIONS[interview["core_index"]]
    if interview["followup_index"] < len(interview["followups"]):
        return interview["followups"][interview["followup_index"]]
    interview["complete"] = True
    return None


def _history(interview: dict[str, Any]) -> list[dict[str, str]]:
    questions = CORE_QUESTIONS + interview.get("followups", [])
    return [
        {"question": questions[index], "answer": answer}
        for index, answer in enumerate(interview["answers"])
        if index < len(questions)
    ]


def _messages(interview: dict[str, Any]) -> list[dict[str, str]]:
    """Return the durable conversation, creating one for legacy/demo interview data."""
    if interview.get("messages"):
        return interview["messages"]
    messages: list[dict[str, str]] = []
    for turn in _history(interview):
        messages.extend([
            {"role": "assistant", "content": turn["question"]},
            {"role": "user", "content": turn["answer"]},
        ])
    if not interview["complete"]:
        question = _next_question(interview)
        if question:
            messages.append({"role": "assistant", "content": question})
    interview["messages"] = messages
    return messages


def _interview_payload(interview: dict[str, Any]) -> dict[str, Any]:
    return {
        "complete": interview["complete"],
        "answered": len(interview["answers"]),
        "total": len(CORE_QUESTIONS) + 2,
        "messages": _messages(interview),
        "ai_assisted": interview.get("ai_assisted", False),
        "ai_available": llm_enabled(),
    }


def _score(markers: dict[str, bool]) -> tuple[int, list[str], list[str]]:
    score = sum(markers.values())
    strengths = [
        label for key, label in {
            "specific_example": "gave a concrete example",
            "personal_action": "explained their personal contribution",
            "outcome": "described an outcome",
            "reflection": "showed reflection and learning",
            "plan": "outlined a practical participation plan",
        }.items() if markers[key]
    ]
    gaps = [
        label for key, label in {
            "specific_example": "a concrete example",
            "personal_action": "their own role",
            "outcome": "a clear outcome",
            "reflection": "reflection on learning",
            "plan": "a practical participation plan",
        }.items() if not markers[key]
    ]
    return score, strengths, gaps


@app.get("/")
def home() -> FileResponse:
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/api/applicants")
def list_applicants() -> list[dict[str, Any]]:
    return [{"id": key, "name": value["name"], "skill": value["skill"], "interview_complete": interviews[key]["complete"]} for key, value in applicants.items()]


@app.post("/api/applicants", status_code=201)
def create_applicant(data: ApplicantIn) -> dict[str, Any]:
    applicant_id = str(uuid4())[:8]
    applicants[applicant_id] = {**data.model_dump(), "created_on": str(date.today())}
    interviews[applicant_id] = _new_interview()
    return {"id": applicant_id, "name": data.name, "message": "Application saved. Your interview is ready."}


@app.get("/api/interviews/{applicant_id}")
def get_interview(applicant_id: str) -> dict[str, Any]:
    if applicant_id not in interviews:
        raise HTTPException(404, "Applicant not found")
    interview = interviews[applicant_id]
    return _interview_payload(interview)


@app.post("/api/interviews/{applicant_id}/answers")
def submit_answer(applicant_id: str, data: AnswerIn) -> dict[str, Any]:
    if applicant_id not in interviews:
        raise HTTPException(404, "Applicant not found")
    interview = interviews[applicant_id]
    if interview["complete"]:
        raise HTTPException(409, "Interview is already complete")
    answer = data.answer.strip()
    try:
        next_answers = [*interview["answers"], answer]
        reply, used_ai = acknowledgement([*_messages(interview), {"role": "user", "content": answer}])
        new_followups = None
        if interview["core_index"] == len(CORE_QUESTIONS) - 1:
            new_followups, followup_ai = tailored_followups(next_answers, _followups(next_answers))
            used_ai = used_ai or followup_ai
    except LLMError as error:
        raise HTTPException(503, str(error)) from error

    interview["answers"].append(answer)
    _messages(interview).extend([
        {"role": "user", "content": answer},
        {"role": "assistant", "content": reply},
    ])
    interview["ai_assisted"] = interview.get("ai_assisted", False) or used_ai
    if interview["core_index"] < len(CORE_QUESTIONS):
        interview["core_index"] += 1
        if new_followups:
            interview["followups"] = new_followups
    else:
        interview["followup_index"] += 1
    question = _next_question(interview)
    if question:
        _messages(interview).append({"role": "assistant", "content": question})
    return _interview_payload(interview)


@app.post("/api/selection")
def select(data: SelectionIn) -> dict[str, Any]:
    if not llm_enabled():
        raise HTTPException(503, "The reviewer assistant needs GEMINI_API_KEY. Add it to backend/.env and restart the server.")
    assessed = []
    for applicant_id, applicant in applicants.items():
        interview = interviews[applicant_id]
        if not interview["complete"]:
            continue
        try:
            markers, markers_ai = evidence_assessment(interview["answers"])
        except LLMError as error:
            raise HTTPException(503, str(error)) from error
        score, strengths, gaps = _score(markers)
        fallback_summary = "Interview evidence: " + ", ".join(strengths[:3] or ["limited specific evidence"])
        try:
            summary, used_ai = evidence_summary(interview["answers"], fallback_summary)
        except LLMError as error:
            raise HTTPException(503, str(error)) from error
        assessed.append({"id": applicant_id, "name": applicant["name"], "skill": applicant["skill"], "score": score, "strengths": strengths, "gaps": gaps, "ai_summary": summary, "ai_assisted": markers_ai or used_ai})
    assessed.sort(key=lambda person: (-person["score"], person["name"].casefold()))
    placements, waitlist = assessed[:data.seats], assessed[data.seats:]
    for index, person in enumerate(placements):
        person["decision"] = "Training place"
        person["guaranteed_job"] = index < 2
        if person["guaranteed_job"]:
            person["decision"] = "Job guaranteed"
            person["reason"] = "Guaranteed job placement because their completed interview showed the strongest evidence of " + ", ".join(person["strengths"][:3]) + "."
        else:
            person["reason"] = "Awarded a training place because their interview showed " + ", ".join(person["strengths"][:3]) + "."
    for person in waitlist:
        person["decision"] = "Waitlist"
        person["guaranteed_job"] = False
        person["reason"] = "Not placed in this round because other completed interviews showed more of the assessed evidence. Evidence still to strengthen: " + ", ".join(person["gaps"][:2] or ["no additional gaps identified"]) + "."
    return {"seats": data.seats, "job_guarantees": min(2, len(placements)), "assessed": len(assessed), "placements": placements, "waitlist": waitlist, "ai_available": llm_enabled(), "note": "Five training places are available; only the two strongest completed interviews receive a guaranteed job placement. Age and residence are collected for administration only and are not used in scoring or tie-breaking."}


@app.post("/api/demo")
def load_demo() -> dict[str, Any]:
    demo = [
        ("Ada Okafor", "Data analysis", ["I want to learn data analysis because I help my aunt track her shop sales and need a better way to spot slow products.", "Last year I organised three months of notebook records into a spreadsheet. I checked totals, asked my aunt about missing receipts, and made a weekly sales summary.", "I built a simple stock list in Google Sheets. It helped us notice a product that had not sold for weeks, so we reduced our next order.", "I can attend in the evenings after work and will practise for four hours each weekend. My sister will cover the shop on class days.", "The main obstacle is electricity, so I will download materials at work and keep printed exercises. I learned that accurate records make decisions much easier.", "A completed dashboard for the shop would show I used the opportunity well."]),
        ("Bola James", "Tailoring", ["I want to improve my tailoring so I can take on alterations from neighbours and earn reliably.", "When my sewing machine broke before a wedding, I asked a local repairer to explain the problem, cleaned the bobbin area, and finished the dress by hand.", "I made two school-uniform repairs for children nearby. Both fitted well and their parents asked me to help again.", "I can attend Saturday sessions and practise three evenings each week with my cousin's machine.", "I learned to check measurements twice. Next time I would leave more time for fittings.", "Keeping before-and-after photos and returning customers would show my progress."]),
        ("Chinedu Obi", "Coding", ["I want to learn coding because technology is important and I need a better future.", "I faced challenges at school but I worked hard with my friends.", "I learned some computer things online and it was good.", "I will try to attend all the training.", "I want to gain skills.", "This course will help me."]),
        ("Dami Yusuf", "Data analysis", ["I want to learn data analysis so I can understand information for community projects.", "At a youth event I collected attendance forms, assigned each a number, and counted age groups in a spreadsheet with two friends.", "I made a chart showing which sessions filled up. The organisers moved the next event to a bigger room and attendance improved.", "I have Sunday afternoons free and a friend will share a laptop with me.", "I would check the forms earlier next time because some handwriting was unclear.", "A short report with accurate charts would show I am ready."]),
        ("Efe Mensah", "Coding", ["I want to learn coding to make useful tools for local businesses.", "I was asked to help a neighbour list deliveries. I mapped the tasks, created a simple form with a no-code tool, and showed her how to use it.", "The form reduced missed addresses over two weeks, and we could see which orders were delayed.", "I will use the library computer on Tuesdays and Thursdays and set aside Saturday mornings for practice.", "I learned to test instructions with the person using the tool. Next time I will ask for feedback sooner.", "A working prototype used by one business would demonstrate progress."]),
        ("Fatima Bello", "Tailoring", ["I want to learn tailoring because I enjoy fashion.", "I have had difficult situations but I keep going.", "I made some items and people liked them.", "I can come when possible.", "I will work hard.", "I want to be successful."]),
        ("Grace Nwosu", "Coding", ["I want to gain coding skills so I can support my small phone-accessories business with a clear inventory system.", "When I regularly ran out of popular chargers, I wrote down every sale for a month, compared the counts, and changed what I reordered.", "I created a labelled storage box system. We stopped losing small items and I could answer customers faster.", "I will study for two hours after closing each Monday, Wednesday, and Friday and practise on Saturday.", "I learned that a simple method is better if I can keep using it. Next time I would start recording sooner.", "A small inventory app with real product data would show I applied the training."]),
    ]
    applicants.clear(); interviews.clear()
    for i, (name, skill, answers) in enumerate(demo):
        applicant_id = f"demo-{i + 1}"
        applicants[applicant_id] = {"name": name, "age": 20 + i, "residence": "Lagos", "skill": skill, "motivation": answers[0], "goal": "Use the skill in a practical local project.", "created_on": str(date.today())}
        interviews[applicant_id] = {"core_index": 4, "answers": answers, "followups": _followups(answers[:4]), "followup_index": 2, "complete": True, "ai_assisted": False}
    return {"message": "Seven completed demo interviews loaded."}
