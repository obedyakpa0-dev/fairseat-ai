"""Scenario-driven fairness evaluation for the community training challenge.

This module captures the sample community-skills scenario described in the
challenge brief and scores applicants by evidence, readiness, and fairness
rules rather than sympathy, first-come order, or influence.
"""

from __future__ import annotations


def build_scenario_applicants() -> list[dict]:
    """Return the six sample applicants described in the brief."""
    return [
        {
            "name": "Amina",
            "skill": "Solar installation",
            "motivation": "I need income immediately to support my children and pay rent.",
            "goal": "I want a stable trade and immediate work opportunities.",
            "need_now": True,
            "vague_experience": False,
            "connection": False,
            "job_offer": False,
            "high_potential": False,
            "teaches_others": False,
            "last_chance": False,
            "evidence_summary": "Amina has concrete field experience and a clear need for immediate income.",
        },
        {
            "name": "Daniel",
            "skill": "Coding",
            "motivation": "I am the strongest learner in my class and want to build practical skills.",
            "goal": "I want to become a software developer and keep learning.",
            "need_now": False,
            "vague_experience": False,
            "connection": False,
            "job_offer": False,
            "high_potential": True,
            "teaches_others": False,
            "last_chance": False,
            "evidence_summary": "Daniel shows high learning potential and clear goals, but not an urgent income need.",
        },
        {
            "name": "Musa",
            "skill": "Tailoring",
            "motivation": "This is my last shot after being rejected twice before.",
            "goal": "I want a stable craft and a sustainable income.",
            "need_now": True,
            "vague_experience": False,
            "connection": False,
            "job_offer": False,
            "high_potential": False,
            "teaches_others": False,
            "last_chance": True,
            "evidence_summary": "Musa has a clear commitment to this path and a valid urgency to make it work.",
        },
        {
            "name": "Njeri",
            "skill": "Solar installation",
            "motivation": "I want to teach others after learning, for free, in my community.",
            "goal": "I want to become a trainer and spread practical skills.",
            "need_now": False,
            "vague_experience": False,
            "connection": False,
            "job_offer": False,
            "high_potential": False,
            "teaches_others": True,
            "last_chance": False,
            "evidence_summary": "Njeri shows community service and teaching intent, but weaker direct job placement need.",
        },
        {
            "name": "Bamidele",
            "skill": "Coding",
            "motivation": "I have informal experience and have done some work before.",
            "goal": "I want to improve my skills and get a role.",
            "need_now": True,
            "vague_experience": True,
            "connection": False,
            "job_offer": False,
            "high_potential": False,
            "teaches_others": False,
            "last_chance": False,
            "evidence_summary": "Bamidele's claims are vague and not supported by clear, verifiable examples.",
        },
        {
            "name": "Zainab",
            "skill": "Tailoring",
            "motivation": "I was recommended by someone influential in the community.",
            "goal": "I want a place in the programme.",
            "need_now": False,
            "vague_experience": False,
            "connection": True,
            "job_offer": False,
            "high_potential": False,
            "teaches_others": False,
            "last_chance": False,
            "evidence_summary": "Zainab's path is connected to influence, not demonstrated merit or evidence.",
        },
    ]


def scenario_rank(applicants: dict, interviews: dict, seats: int = 5) -> list[dict]:
    """Deterministically rank applicants using evidence, readiness, and fairness rules.

    The logic deliberately penalises connection-based selection, vague claims, and
    job-offer-driven priority changes after a new fact arrives. It keeps a stable
    ordering that can be explained and challenged.
    """
    ranked = []
    for applicant_id, applicant in applicants.items():
        interview = interviews.get(applicant_id, {})
        flags = interview.get("evidence_flags", {})
        evidence_points = sum(1 for key in ("specific_example", "personal_action", "outcome", "reflection", "plan") if flags.get(key))

        score = evidence_points * 5
        if applicant.get("need_now"):
            score += 3
        if applicant.get("last_chance"):
            score += 2
        if applicant.get("high_potential"):
            score += 3
        if applicant.get("teaches_others"):
            score += 1
        if applicant.get("connection"):
            score -= 8
        if applicant.get("vague_experience"):
            score -= 6
        if applicant.get("job_offer"):
            score -= 5

        if applicant.get("job_offer") and applicant.get("need_now"):
            score -= 2

        reason = (
            "Strong evidence, clear readiness, and a fair case for placement."
            if score >= 15
            else "Solid but lower evidence or weaker fit than the top-ranked candidates."
            if score >= 10
            else "Not selected because the evidence, relevance, or fairness checks did not clear the bar."
        )

        ranked.append({
            "applicant_id": applicant_id,
            "name": applicant.get("name", applicant_id),
            "score": score,
            "completed_interview": bool(interview.get("complete")),
            "evidence_flags": flags,
            "reason": reason,
            "needs_explanation": applicant.get("need_now") or applicant.get("last_chance") or applicant.get("teaches_others") or applicant.get("connection") or applicant.get("vague_experience"),
        })

    return sorted(
        ranked,
        key=lambda item: (not item["completed_interview"], -item["score"], item["applicant_id"]),
    )[: seats]
