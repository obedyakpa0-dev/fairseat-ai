# Fairseat AI

An evidence-led placement prototype for the supplied skills-training challenge. It interviews every applicant with the same four foundation questions, generates at least two evidence probes, and ranks only completed interviews. Age, residence, application order, and personal connections are never used for scoring.

## Run locally

```powershell
cd backend
.\venv\Scripts\python.exe -m uvicorn main:app --reload
```

Open `http://127.0.0.1:8000`. Use **Load completed demo interviews** to see a five-seat decision and individual explanations.

## Enable tailored AI follow-ups

The application uses Google Gemini (`gemini-2.5-flash`) via the `google-genai` SDK to run the interview conversation: it acknowledges each answer, writes two neutral evidence-seeking follow-up questions after the shared foundation interview, assesses five job-relevant evidence dimensions, and produces reviewer-facing evidence summaries. The complete chat transcript is returned by the API and remains visible when an applicant revisits the interview. The server converts only those evidence flags into a deterministic score and placement order; the model never directly selects, rejects, or promises employment.

1. Copy `backend/.env.example` to `backend/.env`.
2. Add `GEMINI_API_KEY` to `.env` (keep this file private and never expose the key in the browser).
3. Restart the server.

The LLM is required for applicant messages and reviewer summaries. If the key, model access, or connection is unavailable, the app reports the error and does not silently replace the model with scripted answers.
