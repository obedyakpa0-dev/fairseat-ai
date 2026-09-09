def _score(applicant, interview):
    answers = " ".join(interview.get("answers", [])).lower()
    skill = applicant.get("skill_of_interest", "").lower()
    motivation = applicant.get("motivation", "").lower()
    goal = applicant.get("goal_after_training", "").lower()

    evidence = len(interview.get("claims", []))
    relevant_terms = sum(
        term in answers
        for term in (skill, motivation, goal)
        if term
    )
    specificity = sum(
        marker in answers for marker in ("because", "for example", "result", "learned", "built")
    )
    return evidence * 3 + relevant_terms * 2 + specificity


def rank_applicants(applicants, interviews, seats):
    ranked = []
    for applicant_id, applicant in applicants.items():
        interview = interviews.get(applicant_id, {})
        score = _score(applicant, interview)
        ranked.append({
            "applicant_id": applicant_id,
            "score": score,
            "completed_interview": interview.get("complete", False),
            "reason": (
                "Selected for demonstrated evidence, relevant goals, and specific reflection."
                if score > 0 else
                "Not selected because the submitted answers did not yet provide enough relevant evidence."
            ),
        })
    return sorted(ranked, key=lambda item: (-item["score"], item["applicant_id"]))