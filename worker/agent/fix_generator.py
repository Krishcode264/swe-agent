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


def parse_ticket(ticket_json: str) -> dict:
    """
    Parse an incident ticket JSON and extract structured information.
    """
    prompt = PARSE_TICKET_PROMPT.format(ticket_json=ticket_json)
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
            "incident_id": "unknown",
            "service": "unknown",
            "error_message": response,
            "hypothesis": response,
        }


def analyze_code(
    incident_id: str,
    service: str,
    error_message: str,
    hypothesis: str,
    file_path: str,
    file_content: str,
) -> str:
    """
    Analyze a code file in the context of an incident to identify the root cause.
    """
    prompt = ANALYZE_CODE_PROMPT.format(
        incident_id=incident_id,
        service=service,
        error_message=error_message,
        hypothesis=hypothesis,
        file_path=file_path,
        file_content=file_content,
    )
    # Could use gemini-2.5-pro here, but sticking to flash for safety against rate limits
    return _call_gemini(prompt, model_name="gemini-2.5-flash")


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
        )
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Failed to parse fix response: {e}. Raw: {response[:500]}")
        raise ValueError(f"Gemini returned an unparseable fix response: {e}")


def generate_retry_fix(
    file_path: str,
    original_snippet: str,
    new_snippet: str,
    test_output: str,
) -> Fix:
    """
    Generate a revised fix after the previous attempt failed tests.
    """
    prompt = RETRY_PROMPT.format(
        file_path=file_path,
        original_snippet=original_snippet,
        new_snippet=new_snippet,
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
        )
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Failed to parse retry fix response: {e}. Raw: {response[:500]}")
        raise ValueError(f"Gemini returned an unparseable retry fix response: {e}")
