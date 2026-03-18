"""
Setup diagnosis — uses LLM to analyze setup/build failures and suggest fixes.
"""

import logging
import json
from typing import Optional, Dict, Any

from agent.fix_generator import call_llm, _extract_json
from agent.prompts import SETUP_DIAGNOSIS_PROMPT

logger = logging.getLogger(__name__)

def diagnose_setup_failure(
    incident_id: str,
    service_type: str,
    command: str,
    service_path: str,
    error_log: str
) -> Dict[str, Any]:
    """
    Call the LLM to diagnose a setup/installation failure.
    
    Returns a dict with:
        analysis: str
        can_fix_automatically: bool
        suggested_command: str
        is_system_limit: bool
        explanation_for_human: str
    """
    logger.info(f"Diagnosing setup failure for {incident_id} ({command})")
    
    prompt = SETUP_DIAGNOSIS_PROMPT.format(
        incident_id=incident_id,
        service_type=service_type,
        command=command,
        service_path=service_path,
        error_log=error_log[:5000] # Cap log size
    )
    
    try:
        response = call_llm(prompt)
        diagnosis = _extract_json(response)
        return diagnosis
    except Exception as e:
        logger.error(f"Failed to diagnose setup failure: {e}")
        return {
            "analysis": f"Failed to parse LLM diagnosis: {str(e)}",
            "can_fix_automatically": False,
            "suggested_command": "",
            "is_system_limit": False,
            "explanation_for_human": "The setup failed and the agent's diagnosis system also encountered an error."
        }
