"""Gemini-assisted interview prompts with a deterministic fairness fallback."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().with_name(".env"))

try:
    from google import genai
    from google.genai import types
except ImportError:  # The app remains runnable before the SDK is installed.
    genai = None
    types = None


MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


class LLMError(RuntimeError):
    """Raised when a required language-model turn cannot be completed."""


def enabled() -> bool:
    return bool(genai and os.getenv("GEMINI_API_KEY"))


def _client() -> genai.Client:
    if not enabled():
        raise LLMError("The interview assistant needs GEMINI_API_KEY. Add it to backend/.env and restart the server.")
    return genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def _questions(text: str) -> list[str]:
    """Accept precisely two short, ordinary questions from the model response."""
    questions = []
    for line in text.splitlines():
        question = re.sub(r"^\s*(?:\d+[.)]|[-•])\s*", "", line).strip(' "')
        if question.endswith("?") and 15 <= len(question) <= 280:
            questions.append(question)
    return questions[:2]


def tailored_followups(answers: list[str], fallback: list[str]) -> tuple[list[str], bool]:
    """Return two neutral evidence probes, without letting the model decide outcomes."""
    instructions = """You are Fairseat's neutral interview facilitator. Based only on the applicant's
four answers, write exactly two short follow-up questions. Each question should help the person give
concrete evidence about their personal action, outcome, reflection, or realistic learning plan.
Do not assess, rank, praise, reject, promise a job, or make a placement decision. Do not ask about
age, residence, gender, ethnicity, religion, disability, family status, political views, or contacts.
Return only a numbered list of two questions, each ending in a question mark."""
    transcript = "\n\n".join(f"Answer {index + 1}: {answer}" for index, answer in enumerate(answers))
    try:
        client = _client()
        response = client.models.generate_content(
            model=MODEL,
            contents=transcript,
            config=types.GenerateContentConfig(
                system_instruction=instructions,
                max_output_tokens=220,
            ),
        )
        questions = _questions(response.text or "")
        if len(questions) != 2:
            raise LLMError("The language model returned an invalid follow-up response. Please send the answer again.")
        return questions, True
    except LLMError:
        raise
    except Exception as error:
        raise LLMError("The language model could not complete the follow-up. Check the API key, model access, and connection.") from error


def acknowledgement(messages: list[dict[str, str]]) -> tuple[str, bool]:
    """Generate a short, neutral chat acknowledgement for an applicant's message."""
    instructions = """You are Fairseat's neutral interview facilitator. Acknowledge the applicant's
latest answer in one concise, respectful sentence (maximum 24 words). Do not assess, rank, praise,
promise a job, make a placement decision, or mention protected personal information."""
    transcript = "\n".join(f"{message['role'].upper()}: {message['content']}" for message in messages[-10:])
    try:
        client = _client()
        response = client.models.generate_content(
            model=MODEL,
            contents=transcript,
            config=types.GenerateContentConfig(
                system_instruction=instructions,
                max_output_tokens=70,
            ),
        )
        text = " ".join((response.text or "").split())
        if not 5 <= len(text) <= 220:
            raise LLMError("The language model returned an invalid chat response. Please send the answer again.")
        return text, True
    except LLMError:
        raise
    except Exception as error:
        raise LLMError("The language model could not answer this message. Check the API key, model access, and connection.") from error


def evidence_summary(answers: list[str], fallback: str) -> tuple[str, bool]:
    """Summarise evidence for the reviewer without assigning a score or outcome."""
    instructions = """Summarise only the relevant evidence in these interview answers in one neutral
sentence of 35 words or fewer. Do not rank, score, select, reject, promise employment, infer
personal traits, or mention age, residence, gender, ethnicity, religion, disability, family,
politics, or contacts. Focus on specific action, outcome, reflection, and participation plan."""
    try:
        client = _client()
        response = client.models.generate_content(
            model=MODEL,
            contents="\n\n".join(answers),
            config=types.GenerateContentConfig(
                system_instruction=instructions,
                max_output_tokens=100,
            ),
        )
        text = " ".join((response.text or "").split())
        if not 10 <= len(text) <= 320:
            raise LLMError("The language model returned an invalid review summary.")
        return text, True
    except LLMError:
        raise
    except Exception as error:
        raise LLMError("The language model could not produce the review summary. Check the API key, model access, and connection.") from error


def evidence_assessment(answers: list[str]) -> tuple[dict[str, bool], bool]:
    """Extract only job-relevant evidence; never ask the model to choose applicants."""
    instructions = """Assess the interview answers for evidence only. Return exactly one JSON object with
these five boolean keys: specific_example, personal_action, outcome, reflection, plan.
Set a key true only when the answers contain explicit evidence for it. Do not infer traits or use
age, residence, gender, ethnicity, religion, disability, family, politics, or contacts. Do not score,
rank, select, reject, or recommend the applicant. Return JSON only."""
    try:
        client = _client()
        response = client.models.generate_content(
            model=MODEL,
            contents="\n\n".join(answers),
            config=types.GenerateContentConfig(
                system_instruction=instructions,
                response_mime_type="application/json",
                max_output_tokens=120,
            ),
        )
        assessment = json.loads(response.text or "{}")
        keys = {"specific_example", "personal_action", "outcome", "reflection", "plan"}
        if set(assessment) != keys or not all(isinstance(assessment[key], bool) for key in keys):
            raise LLMError("The language model returned an invalid evidence assessment.")
        return assessment, True
    except LLMError:
        raise
    except Exception as error:
        raise LLMError("The language model could not assess the interview evidence. Check the API key, model access, and connection.") from error

