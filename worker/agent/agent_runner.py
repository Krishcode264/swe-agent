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
from shared.database_client import update_incident_status, push_thought
from sandbox.apply_fix import apply_fix
from sandbox.test_runner import run_tests, install_dependencies
from github_integration.pr_creator import PRCreator
from config import TARGET_REPO
from .fix_generator import (
    parse_ticket,
    analyze_code,
    generate_fix,
    generate_retry_fix,
)
from .tools import (
    list_files,
    read_file,
    search_in_file,
    search_in_directory,
    execute_command,
)
from sandbox.docker_runner import docker_runner
from .prompts import REPORT_PROMPT
from .fix_generator import call_llm

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
    report=None,
    container_id: Optional[str] = None,
    workdir: Optional[str] = None,
) -> tuple[str, str, str]:
    """
    Investigate the codebase to find the root cause.
    Uses file tools to navigate the code, then Claude to analyze.
    Returns: (root_cause, file_path, file_content)
    """
    import re
    files_analyzed = []
    all_files = list_files(service_path)
    logger.info(f"Service has {len(all_files)} files")

    files_to_read = []

    # Step 1: Parse stack trace if available
    if error_message:
        raw = re.findall(r'[\w/\\.-]+\.(?:js|ts|py|go|rs|jsx|tsx)', error_message)
        stack_files = [p.split(':')[0] for p in raw if 'node_modules' not in p]
        for num_file in stack_files:
            for f in all_files:
                if num_file in f or os.path.basename(num_file) in f:
                    matched_path = os.path.join(service_path, f)
                    if matched_path not in files_to_read:
                        files_to_read.append(matched_path)

    # Step 2: Add explicitly affected file if present
    if affected_file:
        for f in all_files:
            if affected_file in f or os.path.basename(affected_file) in f:
                matched_path = os.path.join(service_path, f)
                if matched_path not in files_to_read:
                    files_to_read.append(matched_path)

    # Step 3: Heuristics fallback if stack trace / affected_file yielded nothing
    if not files_to_read and error_message:
        search_results = search_in_directory(service_path, error_message[:80])
        if search_results and not search_results[0].startswith("Error"):
            first_match = search_results[0].split(":")[0]
            files_to_read.append(os.path.join(service_path, first_match))

    if not files_to_read:
        for pattern_dir in ["routes", "views", "controllers", "api", "services"]:
            for f in all_files:
                if pattern_dir in f.lower():
                    files_to_read.append(os.path.join(service_path, f))
                    break
            if files_to_read:
                break

    if not files_to_read:
        for f in all_files:
            if f.endswith(("app.py", "server.py", "index.js", "app.js", "server.js")):
                files_to_read.append(os.path.join(service_path, f))
                break

    if not files_to_read:
        logger.warning(f"Could not find any relevant file to investigate in {service_path}. Returning defaults.")
        return "No relevant file found", "", ""

    # Step 4: Multi-File ReAct Loop (Capped at 3 files)
    root_cause = "Could not find root cause."
    target_file = files_to_read[0] if files_to_read else ""
    file_content = ""
    env_feedback = ""

    for _ in range(5): # Increase loop limit slightly for command feedback
        if not files_to_read:
            break
            
        current_file = files_to_read.pop(0)
        if current_file in files_analyzed:
            continue

        try:
            file_content = read_file(current_file)
            files_analyzed.append(current_file)
            if report:
                report.files_analyzed.append(current_file)
                
            logger.info(f"Investigating: {current_file}")

            hypothesis_with_feedback = str(hypothesis)
            if env_feedback:
                hypothesis_with_feedback += f"\n[Environment Feedback]: {env_feedback}"

            analysis = analyze_code(
                incident_id=incident_id,
                service=service,
                error_message=error_message,
                hypothesis=hypothesis_with_feedback,
                file_path=current_file,
                file_content=file_content,
            )

            # Handle suggested commands
            commands = analysis.get("suggested_commands", [])
            if commands:
                env_feedback = "" # Reset feedback for this round
                for cmd in commands:
                    logger.info(f"Running suggested command: {cmd}")
                    cmd_res = execute_command(cmd, service_path)
                    env_feedback += f"\n$ {cmd}\n{cmd_res}\n"

            root_cause = analysis.get("root_cause_explanation", "")
            target_file = current_file
            
            if analysis.get("found_root_cause"):
                logger.info("Root cause found.")
                break
            else:
                next_files = analysis.get("suggested_next_files", [])
                logger.info(f"Root cause not in {current_file}, LLM suggested: {next_files}")
                for nf in next_files:
                    for f in all_files:
                        if nf in f or os.path.basename(nf) in f:
                            matched = os.path.join(service_path, f)
                            if matched not in files_to_read and matched not in files_analyzed:
                                files_to_read.append(matched)
                                
        except Exception as e:
            logger.warning(f"Failed to investigate {current_file}: {e}")
            continue

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


# These are now handled by sandboxed modules.
def _run_tests_in_service(service_path: str, service_type: str) -> TestResults:
    """Wrapper for the new sandboxed test runner."""
    return run_tests(service_path, service_type=service_type)


def _generate_report_markdown(report: ResolutionReport) -> str:
    # Pausing LLM report generation as requested by user to save local resources
    return f"""# Resolution Report — {report.incident_id}
**Service**: {report.service}
**Hypothesis**: {report.hypothesis}
**Root Cause**: {report.root_cause}
**Fix Applied**: {report.fix.explanation if report.fix else "N/A"}
**Test Status**: {"Passed" if report.test_results and report.test_results.passed else "Failed/Not Run"}
**Confidence**: {report.confidence_score}%
"""


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
    # Extract incident ID
    incident_id = incident.get("incidentId") or incident.get("task_id") or incident.get("id", "unknown")
    
    # Prioritize TARGET_REPO from config if it's set, otherwise use what's in the incident
    incident_repo = incident.get("repository", "")
    if TARGET_REPO and ("Rezinix-AI" in incident_repo or not incident_repo):
        repo_url = f"https://github.com/{TARGET_REPO}.git"
        logger.info(f"Target repo override from .env: {repo_url}")
    else:
        repo_url = incident_repo
        
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

    # Initialize variables for cleanup
    container_id = None
    repo_path = None
    
    try:
        # ── Step 0: Early exit for empty/useless incidents ──
        raw_description = incident.get("description", "").strip()
        raw_error_log = incident.get("error_log", "").strip()
        raw_title = incident.get("title", "").strip()

        # If both description and error log are empty, there's nothing to investigate
        if not raw_description and not raw_error_log and (not raw_title or raw_title.lower() in ["untitled", "untitiled jira issue", "untitled jira issue", ""]):
            logger.warning(f"Incident {incident_id} has no description or error log — marking as insufficient_data.")
            push_thought(incident_id, "⚠️ This incident has no description or error log. Cannot investigate without more information.")
            update_incident_status(incident_id, "completed", "Insufficient data: no description or error log provided. Please add details to the issue.")
            return report

        # ── Step 1: Parse the ticket ──
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
        report.service = service
        logger.info(f"Parsed ticket: service={service}, hypothesis={hypothesis[:100]}")
        push_thought(incident_id, f"🔍 Parsed ticket. Identified service: '{service}'. Initial hypothesis: {hypothesis}")

        # ── Step 2: Clone/locate the repository ──
        update_incident_status(incident_id, "cloning", "Cloning repository")
        from agent.repo_manager import clone_repo, create_branch, commit_fix, commit_all_changes, has_uncommitted_changes, push_branch, cleanup_repo

        repo_path = clone_repo(repo_url or "https://github.com/Rezinix-AI/shopstack-platform.git")
        service_path = _detect_service_root(repo_path, service)
        
        # ── Step 2.1: Start Docker Sandbox ──
        service_type = "python" if service.lower().startswith("python") else "node"
        image_name = "python:3.11-slim" if service_type == "python" else "node:20-alpine"
        
        update_incident_status(incident_id, "cloning", f"Starting Docker sandbox ({image_name})")
        
        # Mount the entire repo for maximum flexibility
        volume_mounts = {repo_path: {'bind': '/app', 'mode': 'rw'}}
        container_id = docker_runner.create_sandbox(image_name, volume_mounts)
        
        if not container_id:
            logger.error("Failed to start Docker sandbox. Falling back to local execution.")
            push_thought(incident_id, "⚠️ Docker sandbox failed to start — falling back to local execution mode.")
        else:
            logger.info(f"Docker sandbox started: {container_id[:12]}")
            push_thought(incident_id, f"🐳 Docker sandbox ready ({image_name}). Repository volume-mounted at /app.")
        
        # Use issue_number for branch name if available (e.g. fix/42), else use incident_id
        issue_number = incident.get("issue_number")
        branch_name = f"fix/{issue_number}" if issue_number else f"fix/{incident_id.lower()}"
        create_branch(repo_path, branch_name)
        
        # ── Step 2.5: Install Dependencies (Sandbox Robustness) ──
        update_incident_status(incident_id, "cloning", "Installing dependencies in sandbox")
        
        # Map local service_path to container path
        container_service_path = os.path.join("/app", os.path.relpath(service_path, repo_path)) if container_id else service_path
        
        install_dependencies(
            service_path, 
            service_type=service_type, 
            container_id=container_id,
            workdir=container_service_path
        )

        # ── Step 3: Investigate the codebase ──
        update_incident_status(incident_id, "investigating", "Analyzing codebase for root cause")
        root_cause, target_file, file_content = _investigate_codebase(
            incident_id=incident_id,
            service=service,
            error_message=error_message,
            hypothesis=hypothesis,
            service_path=service_path,
            affected_file=affected_file,
            report=report,
            container_id=container_id,
            workdir=container_service_path
        )
        report.root_cause = root_cause
        push_thought(incident_id, f"🧠 Root cause identified: {root_cause[:200]}. Target file: {target_file}")

        # ── Step 4: Generate and apply fix (with retry loop) ──
        fix = None
        test_results = None
        previous_attempts_history = ""
        any_fix_applied = False

        for attempt in range(1, MAX_RETRIES + 2):
            report.retry_count = attempt

            if attempt == 1:
                update_incident_status(incident_id, "fixing", f"Generating fix (attempt {attempt})")
                fix = generate_fix(
                    incident_id=incident_id,
                    root_cause=root_cause,
                    file_path=target_file,
                    file_content=file_content,
                    error_log=error_message,
                )
            else:
                update_incident_status(incident_id, "retrying", f"Revising fix based on test failure (attempt {attempt})")
                fix = generate_retry_fix(
                    file_path=target_file,
                    previous_attempts=previous_attempts_history,
                    test_output=test_results.output[:3000] if test_results else "",
                )
                file_content = read_file(target_file)

            report.fix = fix
            logger.info(f"Fix attempt {attempt}: {fix.explanation}")
            push_thought(incident_id, f"🔧 Fix attempt {attempt}: {fix.explanation}")
            previous_attempts_history += f"Attempt {attempt}:\nFile: {target_file}\nExplanation: {fix.explanation}\nOriginal: {fix.original_snippet}\nNew: {fix.new_snippet}\n"

            applied = apply_fix(repo_path, fix)
            if not applied and not fix.no_fix_needed:
                logger.error(f"Failed to apply fix on attempt {attempt}")
                continue

            any_fix_applied = True
            if fix.no_fix_needed:
                logger.info("Fix generation stated no fix needed. Stopping retries.")
                break

            update_incident_status(incident_id, "fix_applied", "Fix applied, running tests")

            # Run tests (pass container_id if available)
            test_results = run_tests(service_path, service_type=service_type, container_id=container_id, workdir=container_service_path)
            report.test_results = test_results
            previous_attempts_history += f"Test Output:\n{test_results.output[:1000]}\n" + "-" * 40 + "\n"

            env_error_keywords = ["WinError 2", "ENOENT", "command not found", "MODULE_NOT_FOUND"]
            if any(kw in test_results.output for kw in env_error_keywords):
                logger.warning("Environment error detected — skipping retries.")
                fix.no_fix_needed = True
                fix.explanation = f"Skipped: environment error ({test_results.output[:120]})"
                report.env_error_detected = True
                break

            if test_results.passed:
                logger.info(f"Tests PASSED on attempt {attempt}!")
                update_incident_status(incident_id, "tests_passed", "All tests passed")
                push_thought(incident_id, f"✅ Tests passed on attempt {attempt}! The fix works correctly.")
                break
            else:
                logger.warning(f"Tests FAILED on attempt {attempt}: {test_results.output[:200]}")
                push_thought(incident_id, f"❌ Tests failed on attempt {attempt}. Output snippet: {test_results.output[:150]}. Revising the fix...")
                if attempt > MAX_RETRIES:
                    update_incident_status(incident_id, "partial_fix", f"Fix applied but tests still failing after {MAX_RETRIES + 1} attempts")

        # ── Step 5: Calculate confidence score ──
        if report.env_error_detected:
            report.confidence_score = max(50, 80 - (report.retry_count - 1) * 10)
        elif test_results and test_results.passed:
            report.confidence_score = max(60, 95 - (report.retry_count - 1) * 15)
        elif test_results:
            report.confidence_score = max(10, 40 - (report.retry_count - 1) * 10)
        else:
            report.confidence_score = 10

        # ── Step 6: Generate report markdown ──
        update_incident_status(incident_id, "reporting", "Generating resolution report")
        report.report_markdown = _generate_report_markdown(report)

        # ── Step 7: Create PR ──
        # IMPORTANT: Only create a PR if we actually patched a source file.
        # Git side-effects (e.g. npm install creating package-lock.json) must NOT trigger a PR.
        # If no_fix_needed=True, the agent determined this is not a code-fixable problem — skip PR.
        has_file_patch = any_fix_applied and report.fix and not report.fix.no_fix_needed

        if has_file_patch:
            logger.info("A source-code fix was applied. Proceeding with PR creation.")
            try:
                pr_creator = PRCreator()
                commit_fix(repo_path, target_file, incident_id)
                push_branch(repo_path, branch_name)
                # Prefer the real GitHub issue number (e.g., #42) for the PR title
                # so GitHub auto-links and closes the issue on merge.
                github_issue_number = incident.get("issue_number")
                if github_issue_number:
                    pr_title = f"Fix #{github_issue_number}: {incident.get('title', incident_id)}"
                    closes_ref = f"\n\n---\nCloses #{github_issue_number}"
                else:
                    # Fallback for manually simulated incidents (no real GitHub issue)
                    pr_title = f"Fix: {incident.get('title', incident_id)}"
                    closes_ref = ""

                pr_url = pr_creator.create_pull_request(
                    repo_name=repo_url.split("github.com/")[-1].replace(".git", ""),
                    branch_name=branch_name,
                    title=pr_title,
                    body=report.report_markdown + closes_ref
                )
                report.pr_url = pr_url
                push_thought(incident_id, f"🚀 PR created: {pr_url}")
                update_incident_status(incident_id, "pr_created", f"PR created: {pr_url}")
                update_incident_status(incident_id, "completed", "Incident resolved successfully with PR.")
            except Exception as e:
                logger.error(f"Failed to create PR: {e}")
                update_incident_status(incident_id, "pr_failed", f"PR creation failed: {e}")
        elif report.fix and report.fix.no_fix_needed:
            # Agent correctly determined this cannot be fixed with a code change
            reason = report.fix.explanation or "Not a code-fixable issue"
            logger.info(f"Skipping PR — agent determined no code fix needed: {reason}")
            push_thought(incident_id, f"⚠️ No PR created: {reason}")
            update_incident_status(incident_id, "completed", f"No code fix required: {reason}")
        else:
            logger.info("No code changes detected — skipping PR creation.")
            update_incident_status(incident_id, "completed", "No code changes were produced.")

        return report

    except Exception as e:
        logger.error(f"Agent workflow failed for {incident_id}: {e}")
        update_incident_status(incident_id, "failed", f"Agent workflow failed: {e}")
        report.root_cause = f"Agent failed: {e}"
        report.confidence_score = 0
        return report

    finally:
        # ── Cleanup ──
        if container_id:
            try:
                docker_runner.destroy_sandbox(container_id)
                logger.info(f"Cleaned up Docker sandbox: {container_id[:12]}")
            except Exception as e:
                logger.warning(f"Failed to cleanup Docker sandbox: {e}")
        
        # We don't necessarily want to cleanup the repo if we need it for logs,
        # but the original code had it here.
        # if repo_path:
        #     cleanup_repo(repo_path)
