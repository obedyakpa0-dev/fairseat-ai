def generate_follow_up_questions(claims):
    follow_up_questions = []
    for claim in claims:
        if claim['evidence_strength'] == 'unsupported':
            follow_up_questions.append(f"Can you provide more details about {claim['claim'].lower().replace('applicant claims', '')}?")
    return follow_up_questions
