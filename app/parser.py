import os
import json
import re
import httpx
from dotenv import load_dotenv
from google import genai

# Load .env
load_dotenv()

# Read API key
api_key = os.getenv("GEMINI_API_KEY")

# Don't crash the whole app at import time if this is missing/bad —
# that would take down EVERY route (skills, applications, auth, etc.),
# not just the AI-powered ones. Instead, fail only when something
# actually tries to use the Gemini client.
_client = None


def _get_client():
    global _client
    if _client is None:
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY not found in .env — set it to use AI features "
                "(job parsing, cover letters, resume tailoring, etc.)"
            )
        _client = genai.Client(api_key=api_key)
    return _client


class _LazyClientProxy:
    """Lets other modules keep doing `from parser import client` and
    `client.models.generate_content(...)` unchanged, but defers the real
    genai.Client() construction (and the credential check) until first use."""

    @property
    def models(self):
        return _get_client().models


client = _LazyClientProxy()

# Centralized so a future Gemini model deprecation only needs one change, not
# seven. gemini-2.5-flash was retired ("no longer available to new users") —
# gemini-3.5-flash is the current stable, GA model as of July 2026.
GEMINI_MODEL = "gemini-2.5-flash-lite"

EXTRACTION_PROMPT = """
You are an expert job parser.

Extract the following information and return ONLY valid JSON.

{{
  "company": "",
  "role": "",
  "requirements": [],
  "key_skills": [],
  "location": "",
  "employment_type": "",
  "seniority": ""
}}

Job Description:

{job_text}
"""


def fetch_url_text(url: str) -> str:
    response = httpx.get(
        url,
        timeout=20,
        follow_redirects=True,
        headers={"User-Agent": "Mozilla/5.0"},
    )

    response.raise_for_status()

    text = response.text

    text = re.sub(r"<script.*?</script>", "", text, flags=re.S)
    text = re.sub(r"<style.*?</style>", "", text, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text[:15000]


def parse_job(job_url=None, raw_text=None):

    if not job_url and not raw_text:
        raise ValueError("Provide either job_url or raw_text")

    job_text = raw_text if raw_text else fetch_url_text(job_url)

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=EXTRACTION_PROMPT.format(job_text=job_text),
    )

    result = response.text.strip()

    result = result.replace("```json", "")
    result = result.replace("```", "").strip()

    return json.loads(result)