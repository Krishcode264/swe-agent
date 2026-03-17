"""
Fix generator — uses Gemini LLM to analyze code and generate minimal fixes.

This module handles:
  1. Parsing incident tickets to extract structured context
  2. Analyzing relevant code files to identify root causes
  3. Generating minimal, correct code patches
"""

import json
import logging
from typing import Optional

from google import genai

from config import GEMINI_API_KEY
from shared.models import Fix
from agent.prompts import (
    PARSE_TICKET_PROMPT,
    ANALYZE_CODE_PROMPT,
    GENERATE_FIX_PROMPT,
    RETRY_PROMPT,
)

logger = logging.getLogger(__name__)

# Initialize Gemini client
_client: Optional[genai.Client] = None


def _get_client() -> genai.Client:
    """Lazy-initialize the Gemini client."""
    global _client
    if _client is None:
        if not GEMINI_API_KEY:
            raise ValueError(
                "GEMINI_API_KEY is not set. Add it to your .env file."
            )
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


def _call_gemini(prompt: str, model_name: str = "gemini-2.5-flash") -> str:
    """
    Make a single Gemini API call and return the text response.
    Centralized here so all LLM calls go through one function.
    Using gemini-2.5-flash by default as it is fast and has high rate limits.
    """
    client = _get_client()
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt
        )
        return response.text
    except Exception as e:
        logger.error(f"Gemini API call failed: {e}")
        raise


def parse_ticket(
    incident_id: str,
    repository: str,
    issue_number,
    title: str,
    description: str,
    error_log: str,
) -> dict:
    """
    Parse an incident's pre-extracted fields and use Gemini to:
    1. Classify the service/language.
    2. Generate a root-cause hypothesis.

    All heavy extraction is already done by Krishna's webhook — we only ask Gemini
    for what it's actually best at: reasoning and classification.

    Args:
        incident_id: The incident ID (e.g. "INC-0042").
        repository: The GitHub repo full name (e.g. "Rezinix-AI/shopstack-platform").
        issue_number: The GitHub issue number (int or empty string).
        title: The issue title.
        description: The full issue body text.
        error_log: The pre-extracted error log / stack trace.

    Returns:
        Dictionary with: service, error_type, error_message, affected_file, hypothesis.
    """
    prompt = PARSE_TICKET_PROMPT.format(
        incident_id=incident_id,
        repository=repository,
        issue_number=issue_number,
        title=title,
        description=description,
        error_log=error_log or "Not provided",
    )
    response = _call_gemini(prompt)

    try:
        cleaned = response.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1])
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning(f"Failed to parse ticket response as JSON, returning raw: {response[:200]}")
        return {
            "incident_id": incident_id,
            "service": "unknown",
            "error_message": error_log[:300] if error_log else response,
            "hypothesis": response[:300],
        }



def analyze_code(
    incident_id: str,
    service: str,
    error_message: str,
    hypothesis: str,
    file_path: str,
    file_content: str,
) -> dict:
    """
    Analyze a code file in the context of an incident to identify the root cause.
    Returns a dict with found_root_cause, root_cause_explanation, and suggested_next_files.
    """
    prompt = ANALYZE_CODE_PROMPT.format(
        incident_id=incident_id,
        service=service,
        error_message=error_message,
        hypothesis=hypothesis,
        file_path=file_path,
        file_content=file_content,
    )
    response = _call_gemini(prompt, model_name="gemini-2.5-flash")
    
    try:
        cleaned = response.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1])
        if cleaned.startswith("json\n"):
            cleaned = cleaned[5:]
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning(f"Failed to parse analyze_code response as JSON. Raw: {response[:200]}")
        return {
            "found_root_cause": True, # Assume true as a fallback
            "root_cause_explanation": response,
            "suggested_next_files": []
        }


def generate_fix(
    incident_id: str,
    root_cause: str,
    file_path: str,
    file_content: str,
) -> Fix:
    """
    Generate a minimal code fix for the identified root cause.
    """
    prompt = GENERATE_FIX_PROMPT.format(
        incident_id=incident_id,
        root_cause=root_cause,
        file_path=file_path,
        file_content=file_content,
    )
    response = _call_gemini(prompt, model_name="gemini-2.5-flash")

    try:
        cleaned = response.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1])
            
        # Optional: strip language tags if any from the backticks
        if cleaned.startswith("json\n"):
            cleaned = cleaned[5:]

        fix_data = json.loads(cleaned)

        return Fix(
            file_path=fix_data.get("file_path", file_path),
            explanation=fix_data.get("explanation", ""),
            original_snippet=fix_data.get("original_snippet", ""),
            new_snippet=fix_data.get("new_snippet", ""),
            no_fix_needed=fix_data.get("no_fix_needed", False),
        )
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Failed to parse fix response: {e}. Raw: {response[:500]}")
        raise ValueError(f"Gemini returned an unparseable fix response: {e}")


def generate_retry_fix(
    file_path: str,
    previous_attempts: str,
    test_output: str,
) -> Fix:
    """
    Generate a revised fix after previous attempts failed tests.
    Uses cumulative history to avoid repeating mistakes.
    """
    prompt = RETRY_PROMPT.format(
        file_path=file_path,
        previous_attempts=previous_attempts,
        test_output=test_output,
    )
    response = _call_gemini(prompt, model_name="gemini-2.5-flash")

    try:
        cleaned = response.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1])
            
        if cleaned.startswith("json\n"):
            cleaned = cleaned[5:]

        fix_data = json.loads(cleaned)

        return Fix(
            file_path=fix_data.get("file_path", file_path),
            explanation=fix_data.get("explanation", ""),
            original_snippet=fix_data.get("original_snippet", ""),
            new_snippet=fix_data.get("new_snippet", ""),
            no_fix_needed=fix_data.get("no_fix_needed", False),
        )
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Failed to parse retry fix response: {e}. Raw: {response[:500]}")
        raise ValueError(f"Gemini returned an unparseable retry fix response: {e}")
