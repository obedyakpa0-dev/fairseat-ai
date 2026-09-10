# Fairseat AI

This project implements a fair, explainable skills-training placement system for a community scenario with 5 seats and 20+ applicants. It interviews each applicant through a real conversation, asks at least two follow-up questions before forming an opinion, probes vague claims instead of accepting them at face value, and ranks only completed interviews using evidence rather than sympathy, first-come order, personal pressure, or influence.

## The challenge scenario

A community skills-training program has 5 spots left in a solar installation, coding, or tailoring cohort. There are 20+ applicants, but only 2 of the 5 available places can include a guaranteed job placement afterward. The system must decide which applicants receive each seat and explain why.

The challenge includes applicants such as:

- a single mother who needs income now
- a gifted 17-year-old with strong potential but no immediate need
- someone rejected twice before and calling this their last chance
- a retired elder who wants to teach others afterward for free
- someone claiming prior informal experience without clear evidence
- a local business owner's relative who was recommended by an influential person

The bot is not allowed to:

- say "everyone deserves a spot"
- rely on random selection
- prioritise whoever is most sympathetic or most persuasive
- use application order, personal connections, or protected attributes as scoring inputs
- accept vague or unverifiable claims without follow-up probing

## How the app works

The app asks every applicant the same foundation questions, then generates at least two neutral follow-up questions to test evidence, capability, commitment, realism, and learning potential. It keeps the full chat transcript and can revise an earlier lean when new information appears mid-process, such as a new job offer or a material change in circumstances.

It evaluates only evidence-based signals such as:

- specific example
- personal action
- outcome
- reflection
- plan

It does not score age, residence, relationship to local leaders, or application order. The final ranking is deterministic and explainable.

## Run locally

The backend and frontend are separate applications. Start them in two terminals:

```powershell
cd backend
.\venv\Scripts\python.exe -m uvicorn main:app --reload
```

In a second terminal, serve the frontend:

```powershell
cd frontend
python -m http.server 3000
```

Open `http://127.0.0.1:3000` and use the app to add applicants, run interviews, and review placements. The API is available at `http://127.0.0.1:8000`; set `window.FAIRSEAT_API_URL` in `frontend/app.js` when the backend runs elsewhere.

The backend does not serve frontend files. Its `FRONTEND_ORIGIN` environment variable accepts a comma-separated list of allowed browser origins and defaults to the local port-3000 origins.

## Deploy with Docker

1. Create `backend/.env` from `backend/.env.example` and add the key for your selected provider.
2. Build and start both services:

```powershell
docker compose up --build -d
```

3. Open `http://localhost:3000`. The API health response is at `http://localhost:8000/`.

For a hosted deployment, build the frontend image with the public API URL and configure the backend origin:

```powershell
docker build --build-arg API_URL=https://api.example.com -f frontend/Dockerfile .
```

Set `FRONTEND_ORIGIN=https://app.example.com` on the backend service. Keep `GROQ_API_KEY`, `GEMINI_API_KEY`, and any other secrets in the host or deployment platform's secret manager; do not place them in an image or commit them.

## Enable AI follow-ups and evidence review

The application supports GroqCloud and Google Gemini. Set `LLM_PROVIDER=groq` for GroqCloud (recommended default) or `LLM_PROVIDER=gemini` for Google Gemini:

- acknowledge each answer in conversation
- generate two neutral evidence-seeking follow-up questions after the foundation interview
- assess five job-relevant evidence dimensions
- summarise reviewer-facing evidence for completed interviews

It never directly selects, rejects, or promises employment from the model alone. It only converts the evidence flags into a deterministic selection score.

1. Copy `backend/.env.example` to `backend/.env`.
2. Add `GROQ_API_KEY` and keep `LLM_PROVIDER=groq`, or add `GEMINI_API_KEY` and set `LLM_PROVIDER=gemini`.
3. Restart the server.

If the key, model access, or connection is unavailable, the app continues with a neutral guided fallback instead of blocking the interview.

## Fairness and explainability rules

Every placed applicant must be able to be justified individually.
Each non-selected applicant must have a clear reason for not being chosen, such as:

- insufficient evidence or vague claims
- weaker practical fit than higher-ranked applicants
- lower readiness for the training or job outcome
- connection-based influence not supported by evidence

The system is designed to explain both the selected and unselected cases, so a reviewer can challenge a placement and get a reasoned answer, not a vague or emotional one.
