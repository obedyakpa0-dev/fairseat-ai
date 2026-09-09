def analyzer_answer(answer: str):
    claims = []

    if 'years' in answer.lower():
        claims.append({
            'claim': 'Applicant claims prior experience in the field',
            'evidence': None,
            'evidence_strength': 'unsupported'
        })

    if 'built' in answer.lower() or 'developed' in answer.lower():
        claims.append({
            'claim': 'Applicant claims to have built or developed something',
            'evidence': None,
            'evidence_strength': 'unsupported'
        })
    return claims