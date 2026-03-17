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

import requests
from google import genai

from config import GEMINI_API_KEYS, LLM_PROVIDER, OLLAMA_BASE_URL, OLLAMA_MODEL
from shared.models import Fix
from agent.prompts import (
    PARSE_TICKET_PROMPT,
    ANALYZE_CODE_PROMPT,
    GENERATE_FIX_PROMPT,
    RETRY_PROMPT,
)

logger = logging.getLogger(__name__)

# Pool of Gemini clients
_clients: list[genai.Client] = []
_current_client_index = 0

def _get_next_client() -> genai.Client:
    """Rotate and return the next Gemini client from the pool."""
    global _clients, _current_client_index
    
    if not _clients:
        if not GEMINI_API_KEYS:
            raise ValueError("GEMINI_API_KEYS is not set. Add it to your .env file.")
        _clients = [genai.Client(api_key=key) for key in GEMINI_API_KEYS]
    
    client = _clients[_current_client_index]
    _current_client_index = (_current_client_index + 1) % len(_clients)
    return client

import time

def _call_ollama(prompt: str) -> str:
    """Make a call to local Ollama instance."""
    url = f"{OLLAMA_BASE_URL}/api/generate"
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json" if "JSON" in prompt.upper() else ""
    }
    
    try:
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        return data.get("response", "")
    except Exception as e:
        logger.error(f"Ollama API call failed: {e}")
        raise e


def _call_llm(prompt: str, model_name: str = "gemini-2.0-flash") -> str:
    """
    Unified entry point for LLM calls. 
    Routes to either Gemini or Ollama based on configuration.
    """
    if LLM_PROVIDER.lower() == "ollama":
        return _call_ollama(prompt)
    else:
        return _call_gemini(prompt, model_name)

def _call_gemini(prompt: str, model_name: str = "gemini-2.0-flash") -> str:
    """
    Make a Gemini API call and return the text response.
    Rotates through available API keys on 429 (Rate Limit) errors.
    """
    max_retries_per_key = 3
    total_keys = len(GEMINI_API_KEYS) or 1
    
    last_exception = None
    
    # Try each key in the pool
    for key_attempt in range(total_keys):
        client = _get_next_client()
        
        for attempt in range(max_retries_per_key):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
                return response.text
            except Exception as e:
                last_exception = e
                err_str = str(e)
                
                # If it's a rate limit error
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    # If we have multiple keys, switch immediately
                    if total_keys > 1:
                        key_idx = (_current_client_index - 1) % int(total_keys)
                        logger.warning(f"Rate limit hit on key {key_idx}. Switching key...")
                        break 
                    else:
                        # Only one key: wait and retry with backoff
                        # Try to parse suggested wait time from error message
                        wait_time = 15 # Default
                        if "retry in" in err_str.lower():
                            try:
                                # Extract number after 'retry in'
                                parts = err_str.lower().split("retry in")
                                if len(parts) > 1:
                                    wait_time = float(parts[1].strip().split()[0].replace('s', '')) + 1
                            except:
                                pass
                        
                        logger.warning(f"Rate limit hit on single key. Waiting {wait_time:.1f}s before retry {attempt + 1}/{max_retries_per_key}...")
                        time.sleep(wait_time)
                        continue
                
                # For other errors, we might want to retry once on the same key
                if attempt < max_retries_per_key - 1:
                    logger.warning(f"Gemini error: {e}. Retrying same key in 2s...")
                    time.sleep(2)
                    continue
                
                # If we're here, this key is failing for non-rate-limit reasons
                logger.error(f"Gemini API call failed on current key: {e}")
                break # Try next key
                
    # If we exhausted all keys
    logger.error(f"Gemini API call failed after trying all {total_keys} keys. Last error: {last_exception}")
    raise last_exception if last_exception else Exception("Unknown error in _call_gemini")


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
    response = _call_llm(prompt)

    try:
        cleaned = response.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            # Using start/end variables to satisfy linters that dislike inline slices sometimes
            start_idx = 1
            end_idx = -1
            cleaned = "\n".join(lines[start_idx:end_idx])
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
    response = _call_llm(prompt)
    
    try:
        cleaned = response.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            # Using variables for slices to avoid lint issues
            s_idx = 1
            e_idx = -1
            cleaned = "\n".join(lines[s_idx:e_idx])
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
    response = _call_llm(prompt)

    try:
        cleaned = response.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            s_idx = 1
            e_idx = -1
            cleaned = "\n".join(lines[s_idx:e_idx])
            
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
    response = _call_llm(prompt)

    try:
        cleaned = response.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            s_idx = 1
            e_idx = -1
            cleaned = "\n".join(lines[s_idx:e_idx])
            
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
