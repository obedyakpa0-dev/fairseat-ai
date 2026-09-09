"""Deterministic placement ranking based solely on evidence flags.

Age, residence, application order, personal connections, and any other
protected or non-evidence attribute are never used.
"""

# Each flag contributes equally to the score (0–5).
EVIDENCE_KEYS = ("specific_example", "personal_action", "outcome", "reflection", "plan")


def _score(interview: dict) -> int:
    flags = interview.get("evidence_flags", {})
    return sum(1 for key in EVIDENCE_KEYS if flags.get(key))


def rank_applicants(applicants: dict, interviews: dict, seats: int) -> list[dict]:
    """Return all applicants sorted by evidence score, completed interviews first."""
    ranked = []
    for applicant_id, applicant in applicants.items():
        interview = interviews.get(applicant_id, {})
        completed = interview.get("complete", False)
        score = _score(interview) if completed else 0
        ranked.append({
            "applicant_id": applicant_id,
            "score": score,
            "completed_interview": completed,
            "evidence_flags": interview.get("evidence_flags", {}),
            "reason": (
                "Selected based on demonstrated evidence across the interview."
                if score > 0
                else "Not selected: interview incomplete or insufficient evidence provided."
            ),
        })
    # Sort: completed first, then by score descending, then alphabetically for ties
    return sorted(
        ranked,
        key=lambda r: (not r["completed_interview"], -r["score"], r["applicant_id"]),
    )
