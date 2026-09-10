from backend.scenario import build_scenario_applicants, scenario_rank


def _full_evidence_interviews(applicants):
    flags = {
        "specific_example": True,
        "personal_action": True,
        "outcome": True,
        "reflection": True,
        "plan": True,
    }
    return {
        name: {"complete": True, "evidence_flags": dict(flags)}
        for name in applicants
    }


def test_scenario_profiles_include_required_risk_factors():
    applicants = build_scenario_applicants()
    names = {person["name"] for person in applicants}

    assert {"Amina", "Daniel", "Musa", "Njeri", "Bamidele", "Zainab"}.issubset(names)
    assert any(person["need_now"] for person in applicants)
    assert any(person["last_chance"] for person in applicants)
    assert any(person["teaches_others"] for person in applicants)
    assert any(person["vague_experience"] for person in applicants)
    assert any(person["connection"] for person in applicants)


def test_scenario_rank_penalises_connection_and_vague_claims():
    applicants = {person["name"]: person for person in build_scenario_applicants()}
    interviews = _full_evidence_interviews(applicants)

    ranked = scenario_rank(applicants, interviews, seats=5)
    top_names = [item["name"] for item in ranked]

    assert top_names[:4] == ["Musa", "Amina", "Daniel", "Njeri"]
    assert "Bamidele" not in top_names[:4]
    assert "Zainab" not in top_names[:4]
    assert len(top_names) == 5
