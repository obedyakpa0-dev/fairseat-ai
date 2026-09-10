"""Provider-configurable interview prompts with a deterministic fallback."""

from __future__ import annotations

import json
import os
import re
import time
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().with_name(".env"))

try:
    from google import genai
except ImportError:  # The app remains runnable before the SDK is installed.
    genai = None

PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()
MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile") if PROVIDER == "groq" else os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
_gemini_client = None
_llm_backoff_until = 0.0


class LLMError(RuntimeError):
    """Raised when a required language-model turn cannot be completed."""


def enabled() -> bool:
    if PROVIDER == "groq":
        return bool(os.getenv("GROQ_API_KEY"))
    return bool(genai and os.getenv("GEMINI_API_KEY"))


def _client():
    global _gemini_client
    if not enabled():
        key_name = "GROQ_API_KEY" if PROVIDER == "groq" else "GEMINI_API_KEY"
        raise LLMError(f"The interview assistant needs {key_name}. Add it to backend/.env and restart the server.")
    if _gemini_client is None:
        _gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    return _gemini_client


def _generate(instructions: str, contents: str, json_output: bool = False) -> str:
    global _llm_backoff_until
    if time.monotonic() < _llm_backoff_until:
        raise LLMError("The language model is temporarily unavailable; continuing with guided interview mode.")
    try:
        if PROVIDER == "groq":
            request = {
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": instructions},
                    {"role": "user", "content": contents},
                ],
                "temperature": 0,
                "max_tokens": 300,
            }
            if json_output:
                request["response_format"] = {"type": "json_object"}
            request = urllib.request.Request(
                "https://api.groq.com/openai/v1/chat/completions",
                data=json.dumps(request).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=8) as response:
                body = json.loads(response.read().decode("utf-8"))
            return body["choices"][0]["message"].get("content") or ""
        response = _client().interactions.create(
            model=MODEL,
            system_instruction=instructions,
            input=contents,
            timeout=8,
        )
        return response.output_text or ""
    except Exception as error:
        if "429" in str(error) or "quota" in str(error).lower() or "rate limit" in str(error).lower():
            _llm_backoff_until = time.monotonic() + 60
        raise


def _fallback_evidence(answers: list[str]) -> dict[str, bool]:
    text = " ".join(answers).lower()
    return {
        "specific_example": any(word in text for word in ("built", "created", "installed", "organised", "organized", "made")),
        "personal_action": any(word in text for word in ("i ", "my ", "we ")),
        "outcome": any(word in text for word in ("result", "improved", "helped", "changed", "completed")),
        "reflection": any(word in text for word in ("learned", "realized", "realised", "would do", "next time")),
        "plan": any(word in text for word in ("want to", "plan to", "will ", "hope to", "after training")),
    }


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
        questions = _questions(_generate(instructions, transcript))
        if len(questions) != 2:
            raise LLMError("The language model returned an invalid follow-up response. Please send the answer again.")
        return questions, True
    except LLMError:
        return list(fallback), False
    except Exception as error:
        return list(fallback), False


def acknowledgement(messages: list[dict[str, str]]) -> tuple[str, bool]:
    """Generate a short, neutral chat acknowledgement for an applicant's message."""
    instructions = """You are Fairseat's neutral interview facilitator. Acknowledge the applicant's
latest answer in one concise, respectful sentence (maximum 24 words). Do not assess, rank, praise,
promise a job, make a placement decision, or mention protected personal information."""
    transcript = "\n".join(f"{message['role'].upper()}: {message['content']}" for message in messages[-10:])
    try:
        text = " ".join(_generate(instructions, transcript).split())
        if not 5 <= len(text) <= 220:
            raise LLMError("The language model returned an invalid chat response. Please send the answer again.")
        return text, True
    except LLMError:
        return "Thanks for sharing that. Let's continue with the next question.", False
    except Exception as error:
        return "Thanks for sharing that. Let's continue with the next question.", False


def evidence_summary(answers: list[str], fallback: str) -> tuple[str, bool]:
    """Summarise evidence for the reviewer without assigning a score or outcome."""
    instructions = """Summarise only the relevant evidence in these interview answers in one neutral
sentence of 35 words or fewer. Do not rank, score, select, reject, promise employment, infer
personal traits, or mention age, residence, gender, ethnicity, religion, disability, family,
politics, or contacts. Focus on specific action, outcome, reflection, and participation plan."""
    try:
        text = " ".join(_generate(instructions, "\n\n".join(answers)).split())
        if not 10 <= len(text) <= 320:
            raise LLMError("The language model returned an invalid review summary.")
        return text, True
    except LLMError:
        return fallback, False
    except Exception as error:
        return fallback, False


def evidence_assessment(answers: list[str]) -> tuple[dict[str, bool], bool]:
    """Extract only job-relevant evidence; never ask the model to choose applicants."""
    instructions = """Assess the interview answers for evidence only. Return exactly one JSON object with
these five boolean keys: specific_example, personal_action, outcome, reflection, plan.
Set a key true only when the answers contain explicit evidence for it. Do not infer traits or use
age, residence, gender, ethnicity, religion, disability, family, politics, or contacts. Do not score,
rank, select, reject, or recommend the applicant. Return JSON only."""
    try:
        assessment = json.loads(_generate(instructions, "\n\n".join(answers), json_output=True))
        keys = {"specific_example", "personal_action", "outcome", "reflection", "plan"}
        if set(assessment) != keys or not all(isinstance(assessment[key], bool) for key in keys):
            raise LLMError("The language model returned an invalid evidence assessment.")
        return assessment, True
    except LLMError:
        return _fallback_evidence(answers), False
    except Exception as error:
        return _fallback_evidence(answers), False

