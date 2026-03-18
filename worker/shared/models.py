"""
Shared data models for the Autonomous Incident-to-Fix Engineering Agent.

This module defines the shared data contract used by ALL modules:
- agent/ (Shivam) → fills incident_id, ticket_text, hypothesis, root_cause, fix, etc.
- sandbox/ (Krishna) → fills test_results, pr_url
- reports/ (Gaurav) → consumes the entire ResolutionReport

⚠️  DO NOT modify this file without notifying all team members.
     Changes here will break other people's code.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Fix:
    """Represents a single code fix applied to resolve an incident."""
    file_path: str           # Path relative to repo root (e.g., "app/routes/auth.py")
    explanation: str         # Human-readable explanation of what was changed and why
    original_snippet: str    # The exact code before the fix
    new_snippet: str         # The exact code after the fix
    no_fix_needed: bool = False # Set True if the issue is environmental/infra and cannot be patched here


@dataclass
class TestResults:
    """Results from running the test suite after applying a fix."""
    passed: bool             # Did all tests pass?
    output: str              # Full stdout/stderr captured from the test run
    tests_added: List[str] = field(default_factory=list)  # Names of any new tests generated


@dataclass
class ResolutionReport:
    """
    The complete resolution report for a single incident.
    This is the central data structure that flows through the entire system.

    Filled by:
        - Shivam's agent: incident_id, ticket_text, hypothesis, root_cause,
                          files_analyzed, fix, confidence_score, retry_count
        - Krishna's sandbox: test_results, pr_url
        - Gaurav's report generator: report_markdown
    """
    incident_id: str                        # e.g., "INC-001"
    ticket_text: str                        # Raw ticket JSON string
    hypothesis: str                         # Agent's initial hypothesis before confirming
    root_cause: str                         # Confirmed root cause after analysis
    files_analyzed: List[str]               # All file paths the agent read during investigation
    service: str = "unknown"                # The affected service name
    fix: Optional[Fix] = None               # The applied fix (None if agent couldn't generate one)
    test_results: Optional[TestResults] = None  # None if tests haven't run yet
    confidence_score: int = 0               # 0-100, agent's self-assessed certainty
    retry_count: int = 0                    # Number of fix attempts (0 = haven't tried yet)
    pr_url: Optional[str] = None            # GitHub PR URL (None if PR not created yet)
    env_error_detected: bool = False        # True if a test failure was classified as an environment error
    report_markdown: str = ""               # Rendered markdown report (filled by report generator)
