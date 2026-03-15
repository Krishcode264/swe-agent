"""
Agent runner — the core ReAct loop for autonomous incident resolution.

Replaces the original placeholder pipeline with a real LLM-driven agent loop:
  1. Parse incident ticket → extract structured context
  2. Navigate codebase with tools → identify root cause
  3. Generate minimal fix → apply it
  4. Run tests → if fail, retry with error context (max 2 retries)
  5. Return a complete ResolutionReport

This module preserves the original process_incident(incident) interface
so that queue_listener.py can call it without changes.
"""

import json
import logging
import os
from typing import Optional

from shared.models import Fix, TestResults, ResolutionReport
from agent.fix_generator import (
    parse_ticket,
    analyze_code,
    generate_fix,
    generate_retry_fix,
)
from agent.tools import (
    list_files,
    read_file,
    search_in_file,
    search_in_directory,
)
from agent.prompts import REPORT_PROMPT
from agent.fix_generator import _call_gemini

logger = logging.getLogger(__name__)

MAX_RETRIES = 2


def _detect_service_root(repo_path: str, service_name: str) -> str:
    """
    Detect the root directory of the affected service within the repo.

    Args:
        repo_path: Absolute path to the cloned repository root.
        service_name: Service identifier from the ticket (e.g., 'python-service', 'node-service').

    Returns:
        Absolute path to the service's root directory.
    """
    # Map common service names to directory patterns
    service_dirs = {
        "python-service": ["python-service", "python_service", "flask-app", "backend"],
        "python": ["python-service", "python_service", "flask-app", "backend"],
        "node-service": ["node-service", "node_service", "express-app", "api"],
        "node": ["node-service", "node_service", "express-app", "api"],
    }

    candidates = service_dirs.get(service_name.lower(), [service_name])
    for candidate in candidates:
        service_path = os.path.join(repo_path, candidate)
        if os.path.isdir(service_path):
            logger.info(f"Found service directory: {service_path}")
            return service_path

    # Fallback: return repo root
    logger.warning(f"Could not find service directory for '{service_name}', using repo root.")
    return repo_path


def _investigate_codebase(
    incident_id: str,
    service: str,
    error_message: str,
    hypothesis: str,
    service_path: str,
    affected_file: Optional[str] = None,
) -> tuple[str, str, str]:
    """
    Investigate the codebase to find the root cause.

    Uses file tools to navigate the code, then Claude to analyze.

    Returns:
        (root_cause, file_path, file_content) — the confirmed root cause,
        the file containing the bug, and its contents.
    """
    files_analyzed = []

    # Step 1: List the service directory to understand structure
    all_files = list_files(service_path)
    logger.info(f"Service has {len(all_files)} files")

    # Step 2: If ticket mentions a specific file, start there
    target_file = None
    if affected_file:
        # Search for the affected file
        for f in all_files:
            if affected_file in f or os.path.basename(affected_file) in f:
                target_file = os.path.join(service_path, f)
                break

    # Step 3: If no specific file, search for error keywords
    if not target_file and error_message:
        # Extract key terms from the error message
        search_results = search_in_directory(service_path, error_message[:80])
        if search_results and not search_results[0].startswith("Error"):
            # Take the first matching file
            first_match = search_results[0].split(":")[0]
            target_file = os.path.join(service_path, first_match)

    # Step 4: If still no file, look for routes/views/controllers
    if not target_file:
        for pattern_dir in ["routes", "views", "controllers", "api", "services"]:
            for f in all_files:
                if pattern_dir in f.lower():
                    target_file = os.path.join(service_path, f)
                    break
            if target_file:
                break

    if not target_file:
        # Last resort: pick the main entry file
        for f in all_files:
            if f.endswith(("app.py", "server.py", "index.js", "app.js", "server.js")):
                target_file = os.path.join(service_path, f)
                break

    if not target_file:
        raise ValueError(f"Could not find any relevant file to investigate in {service_path}")

    # Step 5: Read the target file
    file_content = read_file(target_file)
    files_analyzed.append(target_file)
    logger.info(f"Investigating: {target_file}")

    # Step 6: Ask Claude to analyze
    root_cause = analyze_code(
        incident_id=incident_id,
        service=service,
        error_message=error_message,
        hypothesis=hypothesis,
        file_path=target_file,
        file_content=file_content,
    )

    return root_cause, target_file, file_content


def _apply_fix_to_file(file_path: str, fix: Fix) -> bool:
    """
    Apply a Fix to an actual file by replacing original_snippet with new_snippet.

    Returns True if the fix was applied successfully.
    """
    try:
        content = read_file(file_path)
        if fix.original_snippet not in content:
            logger.error(f"Original snippet not found in {file_path}")
            return False

        new_content = content.replace(fix.original_snippet, fix.new_snippet, 1)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        logger.info(f"Fix applied to {file_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to apply fix to {file_path}: {e}")
        return False


def _run_tests_in_service(service_path: str, service_type: str) -> TestResults:
    """
    Run tests for the given service. This is a placeholder that will be replaced
    by Krishna's sandbox module (worker/sandbox/test_runner.py).

    For now, detects the test framework and runs via subprocess.
    """
    import subprocess

    try:
        if service_type in ("python", "python-service"):
            # Install deps + run pytest
            subprocess.run(
                ["pip", "install", "-r", "requirements.txt"],
                cwd=service_path,
                capture_output=True,
                timeout=120,
            )
            result = subprocess.run(
                ["python", "-m", "pytest", "-v", "--tb=short"],
                cwd=service_path,
                capture_output=True,
                text=True,
                timeout=120,
            )
        elif service_type in ("node", "node-service"):
            subprocess.run(
                ["npm", "install"],
                cwd=service_path,
                capture_output=True,
                timeout=120,
            )
            result = subprocess.run(
                ["npm", "test"],
                cwd=service_path,
                capture_output=True,
                text=True,
                timeout=120,
            )
        else:
            return TestResults(passed=False, output=f"Unknown service type: {service_type}")

        output = result.stdout + "\n" + result.stderr
        passed = result.returncode == 0

        return TestResults(passed=passed, output=output)

    except subprocess.TimeoutExpired:
        return TestResults(passed=False, output="Tests timed out after 120 seconds.")
    except Exception as e:
        return TestResults(passed=False, output=f"Test execution error: {e}")


def _generate_report_markdown(report: ResolutionReport) -> str:
    """Generate a markdown report using Claude."""
    try:
        prompt = REPORT_PROMPT.format(
            incident_id=report.incident_id,
            ticket_text=report.ticket_text,
            hypothesis=report.hypothesis,
            root_cause=report.root_cause,
            file_path=report.fix.file_path if report.fix else "N/A",
            explanation=report.fix.explanation if report.fix else "N/A",
            original_snippet=report.fix.original_snippet if report.fix else "N/A",
            new_snippet=report.fix.new_snippet if report.fix else "N/A",
            tests_passed=report.test_results.passed if report.test_results else "Not run",
            test_output=report.test_results.output[:2000] if report.test_results else "N/A",
            retry_count=report.retry_count,
            files_analyzed=", ".join(report.files_analyzed),
        )
        return _call_gemini(prompt)
    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        return f"# Resolution Report — {report.incident_id}\n\nReport generation failed: {e}"


def process_incident(incident: dict) -> ResolutionReport:
    """
    Main entry point — processes a single incident through the full agent loop.

    This function preserves the original interface so queue_listener.py
    can call it without changes.

    Args:
        incident: Raw incident dictionary (parsed from JSON ticket).

    Returns:
        A fully populated ResolutionReport.
    """
    # Extract incident ID (support both formats: incidentId and id)
    incident_id = incident.get("incidentId") or incident.get("id", "unknown")
    repo_url = incident.get("repository", "")
    ticket_text = json.dumps(incident, indent=2)

    logger.info(f"=== Starting agent workflow for {incident_id} ===")

    # Initialize the report
    report = ResolutionReport(
        incident_id=incident_id,
        ticket_text=ticket_text,
        hypothesis="",
        root_cause="",
        files_analyzed=[],
    )

    # Import status updater (lazy to avoid circular imports with queue_listener)
    try:
        from queue_listener import update_incident_status
    except ImportError:
        # Running standalone (not from queue), use a no-op
        def update_incident_status(id, status, msg):
            logger.info(f"[{id}] {status}: {msg}")

    try:
        # ── Step 1: Parse the ticket ──
        # Use Krishna's pre-extracted fields directly — much cheaper than asking Gemini to re-extract them
        update_incident_status(incident_id, "parsing", "Parsing incident ticket")
        from agent.prompts import PARSE_TICKET_PROMPT
        parsed = parse_ticket(
            incident_id=incident_id,
            repository=incident.get("repository", repo_url),
            issue_number=incident.get("issue_number", ""),
            title=incident.get("title", ""),
            description=incident.get("description", ""),
            error_log=incident.get("error_log", ""),
        )
        service = parsed.get("service", "unknown")
        error_message = parsed.get("error_message", "")
        hypothesis = parsed.get("hypothesis", "")
        affected_file = parsed.get("affected_file", "")

        report.hypothesis = hypothesis
        logger.info(f"Parsed ticket: service={service}, hypothesis={hypothesis[:100]}")

        # ── Step 2: Clone/locate the repository ──
        update_incident_status(incident_id, "cloning", "Cloning repository")
        from agent.repo_manager import clone_repo, create_branch, commit_fix, push_branch, cleanup_repo

        repo_path = clone_repo(repo_url or "https://github.com/Rezinix-AI/shopstack-platform.git")
        service_path = _detect_service_root(repo_path, service)
        # Use issue_number for branch name if available (e.g. fix/42), else use incident_id
        issue_number = incident.get("issue_number")
        branch_name = f"fix/{issue_number}" if issue_number else f"fix/{incident_id.lower()}"
        create_branch(repo_path, branch_name)

        # ── Step 3: Investigate the codebase ──
        update_incident_status(incident_id, "investigating", "Analyzing codebase for root cause")
        root_cause, target_file, file_content = _investigate_codebase(
            incident_id=incident_id,
            service=service,
            error_message=error_message,
            hypothesis=hypothesis,
            service_path=service_path,
            affected_file=affected_file,
        )
        report.root_cause = root_cause
        report.files_analyzed.append(target_file)

        # ── Step 4: Generate and apply fix (with retry loop) ──
        fix = None
        test_results = None
        service_type = "python" if service.lower().startswith("python") else "node"

        for attempt in range(1, MAX_RETRIES + 2):  # +2 because range is exclusive and attempt starts at 1
            report.retry_count = attempt

            if attempt == 1:
                # First attempt: generate fix from root cause
                update_incident_status(
                    incident_id, "fixing",
                    f"Generating fix (attempt {attempt})"
                )
                fix = generate_fix(
                    incident_id=incident_id,
                    root_cause=root_cause,
                    file_path=target_file,
                    file_content=file_content,
                )
            else:
                # Retry: feed test failure back to Claude
                update_incident_status(
                    incident_id, "retrying",
                    f"Revising fix based on test failure (attempt {attempt})"
                )
                fix = generate_retry_fix(
                    file_path=target_file,
                    original_snippet=fix.original_snippet,
                    new_snippet=fix.new_snippet,
                    test_output=test_results.output[:3000] if test_results else "",
                )
                # Re-read file content (may have changed from previous attempt)
                file_content = read_file(target_file)

            report.fix = fix
            logger.info(f"Fix attempt {attempt}: {fix.explanation}")

            # Apply the fix
            applied = _apply_fix_to_file(target_file, fix)
            if not applied:
                logger.error(f"Failed to apply fix on attempt {attempt}")
                continue

            update_incident_status(incident_id, "fix_applied", "Fix applied, running tests")

            # Run tests
            test_results = _run_tests_in_service(service_path, service_type)
            report.test_results = test_results

            if test_results.passed:
                logger.info(f"Tests PASSED on attempt {attempt}!")
                update_incident_status(incident_id, "tests_passed", "All tests passed")
                break
            else:
                logger.warning(f"Tests FAILED on attempt {attempt}: {test_results.output[:200]}")
                if attempt > MAX_RETRIES:
                    update_incident_status(
                        incident_id, "partial_fix",
                        f"Fix applied but tests still failing after {MAX_RETRIES + 1} attempts"
                    )

        # ── Step 5: Calculate confidence score ──
        if test_results and test_results.passed:
            report.confidence_score = max(60, 95 - (report.retry_count - 1) * 15)
        elif test_results:
            report.confidence_score = max(10, 40 - (report.retry_count - 1) * 10)
        else:
            report.confidence_score = 10

        # ── Step 6: Generate report markdown ──
        update_incident_status(incident_id, "reporting", "Generating resolution report")
        report.report_markdown = _generate_report_markdown(report)

        # ── Step 7: Create PR (if tests passed) ──
        if test_results and test_results.passed:
            try:
                from agent.github_client import create_pull_request
                pr_url = create_pull_request(repo_url, branch_name, incident)
                report.pr_url = pr_url
                update_incident_status(incident_id, "pr_created", f"PR created: {pr_url}")
            except Exception as e:
                logger.error(f"Failed to create PR: {e}")
                update_incident_status(incident_id, "pr_failed", f"PR creation failed: {e}")

        logger.info(f"=== Finished agent workflow for {incident_id} (confidence: {report.confidence_score}) ===")
        return report

    except Exception as e:
        logger.error(f"Agent workflow failed for {incident_id}: {e}")
        update_incident_status(incident_id, "failed", f"Agent workflow failed: {e}")
        report.root_cause = f"Agent failed: {e}"
        report.confidence_score = 0
        return report
