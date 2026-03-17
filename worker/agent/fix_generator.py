"""
Fix generator — uses Gemini LLM to analyze code and generate minimal fixes.

This module handles:
  1. Parsing incident tickets to extract structured context
  2. Analyzing relevant code files to identify root causes
  3. Generating minimal, correct code patches
"""

import json
import logging
import re
from typing import Optional

from google import genai
import requests

from config import GEMINI_API_KEY, LLM_PROVIDER, OLLAMA_BASE_URL, OLLAMA_MODEL
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


def call_llm(prompt: str, model_name: Optional[str] = None) -> str:
    """
    Dispatch LLM calls based on LLM_PROVIDER configuration.
    """
    if LLM_PROVIDER == "ollama":
        return _call_ollama(prompt, model_name or OLLAMA_MODEL)
    else:
        return _call_gemini(prompt, model_name or "gemini-2.5-flash")


def _call_gemini(prompt: str, model_name: str) -> str:
    """
    Make a single Gemini API call and return the text response.
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


def _call_ollama(prompt: str, model_name: str) -> str:
    """
    Make a single Ollama API call and return the text response.
    """
    logger.info(f"Calling Ollama ({model_name}) at {OLLAMA_BASE_URL}")
    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": model_name,
                "prompt": prompt,
                "stream": False,
            },
            timeout=120
        )
        response.raise_for_status()
        return response.json().get("response", "")
    except Exception as e:
        logger.error(f"Ollama API call failed: {e}")
        raise


def _sanitize_json_string(text: str) -> str:
    """
    Pre-process LLM output to fix common malformed JSON patterns:
    - Nested double quotes inside string values (e.g. f-strings with {data["key"]})
    - Single quotes used instead of double quotes for keys
    """
    # Remove markdown code fences
    text = re.sub(r'```(?:json)?\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    text = text.strip()

    # Fix the most common Ollama glitch: f-string nested double quotes inside JSON strings
    # e.g. "new_snippet": "... f'text {data["key"]}' ..."
    # Strategy: find string values and replace inner double quotes with single quotes
    def fix_string_value(m):
        inner = m.group(1)
        # Replace double quotes that appear INSIDE the string value (not at boundaries)
        inner = inner.replace('\\"', '__ESCAPED_QUOTE__')
        # Replace unescaped inner double quotes with single quotes
        parts = inner.split('"')
        # Rejoin without trying to parse - just escape them
        fixed = '\\"'.join(parts)
        fixed = fixed.replace('__ESCAPED_QUOTE__', '\\"')
        return f'"{fixed}"'

    return text


def _extract_json(text: str) -> dict:
    """
    Robust JSON extraction from LLM responses.
    Handles text before/after JSON, markdown blocks, and common formatting quirks.
    """
    cleaned = _sanitize_json_string(text)

    # 1. Try to find content between triple backticks (already stripped above, try again)
    try:
        match = re.search(r'(\{.*\})', cleaned, re.DOTALL)
        if match:
            candidate = match.group(1).strip()
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass
    except Exception:
        pass

    # 2. Try direct parse on the full cleaned text
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 3. Field-by-field regex fallback — handles responses where JSON is near-valid
    # but has internal quote issues (common with local LLMs like Ollama)
    result = {}
    # Match: "key": "value" or "key": true/false/null or "key": number
    scalar_pattern = re.findall(r'"(\w+)"\s*:\s*"((?:[^"\\]|\\.)*)"\s*[,}]', cleaned, re.DOTALL)
    for k, v in scalar_pattern:
        result[k] = v
    bool_pattern = re.findall(r'"(\w+)"\s*:\s*(true|false|null)\s*[,}]', cleaned)
    for k, v in bool_pattern:
        result[k] = {"true": True, "false": False, "null": None}[v]

    if result:
        logger.warning(f"Used field-by-field fallback extraction. Got keys: {list(result.keys())}")
        return result

    logger.error(f"Failed to extract JSON from: {text[:500]}...")
    raise json.JSONDecodeError("Could not extract JSON", text, 0)


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
    response = call_llm(prompt)

    try:
        return _extract_json(response)
    except Exception:
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
    response = call_llm(prompt)
    
    try:
        return _extract_json(response)
    except Exception:
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
    response = call_llm(prompt)

    try:
        fix_data = _extract_json(response)

        return Fix(
            file_path=fix_data.get("file_path", file_path),
            explanation=fix_data.get("explanation", ""),
            original_snippet=fix_data.get("original_snippet", ""),
            new_snippet=fix_data.get("new_snippet", ""),
            no_fix_needed=fix_data.get("no_fix_needed", False),
        )
    except Exception as e:
        logger.error(f"Failed to parse fix response: {e}. Raw: {response[:500]}")
        raise ValueError(f"LLM returned an unparseable fix response: {e}")


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
    response = call_llm(prompt)

    try:
        fix_data = _extract_json(response)

        return Fix(
            file_path=fix_data.get("file_path", file_path),
            explanation=fix_data.get("explanation", ""),
            original_snippet=fix_data.get("original_snippet", ""),
            new_snippet=fix_data.get("new_snippet", ""),
            no_fix_needed=fix_data.get("no_fix_needed", False),
        )
    except Exception as e:
        logger.error(f"Failed to parse retry fix response: {e}. Raw: {response[:500]}")
        raise ValueError(f"LLM returned an unparseable retry fix response: {e}")
