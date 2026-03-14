"""
Fix generator — uses Claude LLM to analyze code and generate minimal fixes.

Replaces the original placeholder that used time.sleep() and hardcoded responses.
This module handles:
  1. Parsing incident tickets to extract structured context
  2. Analyzing relevant code files to identify root causes
  3. Generating minimal, correct code patches
"""

import json
import logging
from typing import Optional

import anthropic

from config import ANTHROPIC_API_KEY
from shared.models import Fix
from agent.prompts import (
    PARSE_TICKET_PROMPT,
    ANALYZE_CODE_PROMPT,
    GENERATE_FIX_PROMPT,
    RETRY_PROMPT,
)

logger = logging.getLogger(__name__)

# Initialize Anthropic client
_client: Optional[anthropic.Anthropic] = None


def _get_client() -> anthropic.Anthropic:
    """Lazy-initialize the Anthropic client."""
    global _client
    if _client is None:
        if not ANTHROPIC_API_KEY:
            raise ValueError(
                "ANTHROPIC_API_KEY is not set. Add it to your .env file."
            )
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


def _call_claude(prompt: str, max_tokens: int = 4096) -> str:
    """
    Make a single Claude API call and return the text response.
    Centralized here so all LLM calls go through one function.
    """
    client = _get_client()
    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text
    except Exception as e:
        logger.error(f"Claude API call failed: {e}")
        raise


def parse_ticket(ticket_json: str) -> dict:
    """
    Parse an incident ticket JSON and extract structured information.

    Args:
        ticket_json: Raw JSON string of the incident ticket.

    Returns:
        Dictionary with extracted fields: incident_id, service, error_type,
        error_message, affected_file, severity, hypothesis, etc.
    """
    prompt = PARSE_TICKET_PROMPT.format(ticket_json=ticket_json)
    response = _call_claude(prompt, max_tokens=2048)

    try:
        # Try to extract JSON from the response
        # Handle cases where Claude wraps JSON in markdown code blocks
        cleaned = response.strip()
        if cleaned.startswith("```"):
            # Remove markdown code block
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

    Args:
        incident_id: The incident ID (e.g., "INC-001").
        service: The affected service name.
        error_message: The error message or stack trace.
        hypothesis: Current hypothesis about the root cause.
        file_path: Path of the file being analyzed.
        file_content: Full contents of the file.

    Returns:
        Claude's analysis as a string — root cause explanation.
    """
    prompt = ANALYZE_CODE_PROMPT.format(
        incident_id=incident_id,
        service=service,
        error_message=error_message,
        hypothesis=hypothesis,
        file_path=file_path,
        file_content=file_content,
    )
    return _call_claude(prompt)


def generate_fix(
    incident_id: str,
    root_cause: str,
    file_path: str,
    file_content: str,
) -> Fix:
    """
    Generate a minimal code fix for the identified root cause.

    Args:
        incident_id: The incident ID.
        root_cause: Confirmed root cause description.
        file_path: Path of the file to fix.
        file_content: Current contents of the file.

    Returns:
        A Fix dataclass with the patch details.
    """
    prompt = GENERATE_FIX_PROMPT.format(
        incident_id=incident_id,
        root_cause=root_cause,
        file_path=file_path,
        file_content=file_content,
    )
    response = _call_claude(prompt)

    try:
        cleaned = response.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1])
        fix_data = json.loads(cleaned)

        return Fix(
            file_path=fix_data.get("file_path", file_path),
            explanation=fix_data.get("explanation", ""),
            original_snippet=fix_data.get("original_snippet", ""),
            new_snippet=fix_data.get("new_snippet", ""),
        )
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Failed to parse fix response: {e}. Raw: {response[:500]}")
        raise ValueError(f"Claude returned an unparseable fix response: {e}")


def generate_retry_fix(
    file_path: str,
    original_snippet: str,
    new_snippet: str,
    test_output: str,
) -> Fix:
    """
    Generate a revised fix after the previous attempt failed tests.

    Args:
        file_path: Path of the file being fixed.
        original_snippet: The original code that was replaced.
        new_snippet: The replacement code from the failed attempt.
        test_output: The test failure output.

    Returns:
        A revised Fix dataclass.
    """
    prompt = RETRY_PROMPT.format(
        file_path=file_path,
        original_snippet=original_snippet,
        new_snippet=new_snippet,
        test_output=test_output,
    )
    response = _call_claude(prompt)

    try:
        cleaned = response.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1])
        fix_data = json.loads(cleaned)

        return Fix(
            file_path=fix_data.get("file_path", file_path),
            explanation=fix_data.get("explanation", ""),
            original_snippet=fix_data.get("original_snippet", ""),
            new_snippet=fix_data.get("new_snippet", ""),
        )
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Failed to parse retry fix response: {e}. Raw: {response[:500]}")
        raise ValueError(f"Claude returned an unparseable retry fix response: {e}")
