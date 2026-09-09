from fastapi import FastAPI
from models import Applicant, InterviewAnswer, SelectionRequest
from interview import create_interview, interviews, next_question
from analyzer import analyzer_answer
from followup import generate_follow_up_questions
from selection import rank_applicants


app = FastAPI(title='Fairseat AI', description='An AI-powered platform for fairseat applications', version='1.0.0')
applicants = {}

@app.get("/")
def home():
    return{
        'message': 'Fairseat AI is running'
    }


@app.post("/applicant")
def create_applicant(applicant: Applicant):
    applicants[applicant.name] = applicant.model_dump()
    return{
        'message': 'Applicant Recieved',
        'applicant_id': applicant.name,
        'applicant': applicant
    }

@app.get("/interviews/{applicant_id}/start")
def start_interview(applicant_id: str):
    if applicant_id not in interviews:
        interviews[applicant_id] = create_interview()
    interview = interviews[applicant_id]
    return {
        'applicant_id': applicant_id,
        'question': next_question(interview),
        'complete': interview['complete'],
    }


@app.post('/interviews/answers')
def submit_answer(data: InterviewAnswer):
    interview = interviews.get(data.applicant_id)

    if not interview:
        return {
            'message': 'Interview not found'
        }

    if interview['complete']:
        return {'message': 'Interview is already complete'}

    claims = analyzer_answer(data.answers)
    interview['claims'].extend(claims)
    interview['answers'].append(data.answers)

    if interview['question_index'] < 4:
        interview['question_index'] += 1
        if interview['question_index'] == 4:
            interview['follow_up_questions'] = generate_follow_up_questions(interview['claims'])
            if len(interview['follow_up_questions']) < 2:
                interview['follow_up_questions'].extend([
                    'What specific result did your previous experience produce?',
                    'What would you do differently after reflecting on that experience?',
                ])
    else:
        interview['follow_up_count'] += 1

    question = next_question(interview)
    return {
        'message': 'Answer submitted successfully',
        'applicant_id': data.applicant_id,
        'answers': interview['answers'],
        'claims': interview['claims'],
        'next_question': question,
        'complete': interview['complete'],
    }


@app.post('/selection')
def selection(data: SelectionRequest):
    ranked = rank_applicants(applicants, interviews, data.seats)
    return {
        'seats': data.seats,
        'placements': ranked[:data.seats],
        'non_placements': ranked[data.seats:],
    }