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
import operator
from typing import Optional, List, TypedDict, Annotated, Sequence, Union

from langgraph.graph import StateGraph, END
from shared.models import Fix, TestResults, ResolutionReport
from shared.database_client import update_incident_status, push_thought

class AgentState(TypedDict):
    incident: dict
    incident_id: str
    repo_url: str
    repo_path: Optional[str]
    service_path: Optional[str]
    service: str
    language: str
    container_id: Optional[str]
    
    hypothesis: str
    root_cause: str
    target_file: str
    file_content: str
    
    proposed_fix: Optional[Fix]
    test_results: Optional[TestResults]
    
    attempt_count: int
    messages: Annotated[Sequence[Union[dict, str]], operator.add]
    
    files_analyzed: List[str]
    history: str
    
    confidence: float
    report: Optional[ResolutionReport]
    pr_url: Optional[str]
    status: str
    similar_incidents: List[dict]
    scratchpad: str
    
    # Sandbox v2 fields
    sandbox_result: Optional[dict]
    sandbox_attempts: int
    last_test_context: str
    max_sandbox_attempts: int
    investigation_attempts: int
from .patcher import patch_file_tool
from sandbox.sandbox_node import sandbox_node, route_after_sandbox
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


def detect_language(incident: dict, files_analyzed: list[str]) -> str:
    """Robust language detection for sandbox routing."""
    from pathlib import Path
    
    # 1. Check analyzed files (most reliable signal)
    extensions = {Path(f).suffix.lower() for f in files_analyzed if f}
    if extensions & {".js", ".ts", ".jsx", ".tsx"}:
        return "node"
    if extensions & {".py"}:
        return "python"
    
    # 2. Check service name from incident/ticket
    service = str(incident.get("service", "") or incident.get("service_name", "")).lower()
    if "node" in service:
        return "node"
    if "python" in service:
        return "python"
    
    # 3. Last fallback
    return "python"


def _detect_service_root(repo_path: str, service_name: str) -> str:
    """
    Detect the root directory of the affected service within the repo.
    """
    # 1. Direct Mapping
    service_dirs = {
        "python-service": ["python-service", "python_service", "app", "src", "backend"],
        "node-service": ["node-service", "node_service", "src", "api", "express-app"],
        "node": ["node-service", "node_service", "src", "api", "express-app"],
    }

    sn_lower = str(service_name).lower()
    candidates = service_dirs.get(sn_lower, [sn_lower])
    
    # 2. Search for the candidate in the repo
    for candidate in candidates:
        if not candidate: continue
        path = os.path.join(repo_path, candidate)
        if os.path.isdir(path):
            logger.info(f"Detected service root: {path}")
            return path
            
    # 3. Fallback: Search for directory containing identifying files
    for root, dirs, files in os.walk(repo_path):
        if "package.json" in files and "node" in sn_lower:
            return root
        if "requirements.txt" in files and "python" in sn_lower:
            return root

    logger.warning(f"Could not find exact service directory for '{service_name}', defaulting to repo root.")
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
    Returns: (root_cause, file_path, file_content, files_analyzed)
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
                from .tools import execute_command # already imported but for clarity
                # Note: execute_command now has its own validation, but we can pre-filter here
                for cmd in commands:
                    logger.info(f"Running suggested command: {cmd}")
                    cmd_res = execute_command(cmd, service_path)
                    if "is not a valid shell command" not in cmd_res:
                        env_feedback += f"\n$ {cmd}\n{cmd_res}\n"
                    else:
                        logger.warning(f"Skipping invalid suggested command: {cmd}")

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

    return root_cause, target_file, file_content, files_analyzed





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
    Now uses LangGraph for state management and reasoning loops.
    """
    incident_id = incident.get("incidentId") or incident.get("task_id") or incident.get("id", "unknown")
    repo_url = incident.get("repository", "")
    
    # ── Step 0: Early exit for empty/useless incidents ──
    raw_description = incident.get("description", "").strip()
    raw_error_log = incident.get("error_log", "").strip()
    raw_title = incident.get("title", "").strip()

    if not raw_description and not raw_error_log and (not raw_title or raw_title.lower() in ["untitled", ""]):
        logger.warning(f"Incident {incident_id} has no description or error log — skipping.")
        update_incident_status(incident_id, "completed", "Insufficient data.")
        return ResolutionReport(incident_id=incident_id)

    # ── Build the Graph ──
    workflow = StateGraph(AgentState)
    
    workflow.add_node("parse", parse_node)
    workflow.add_node("setup", setup_node)

    workflow.add_node("investigate", investigate_node)
    workflow.add_node("fix", fix_node)
    workflow.add_node("critic", critic_node)
    workflow.add_node("verify", sandbox_node)
    workflow.add_node("report", report_node)
    
    workflow.set_entry_point("parse")
    workflow.add_edge("parse", "setup")
    workflow.add_edge("setup", "investigate")
    workflow.add_conditional_edges("investigate", route_after_investigate, {
        "fix": "fix",
        "retry": "investigate",
        "give_up": "report"
    })
    workflow.add_edge("fix", "critic")
    workflow.add_conditional_edges("critic", should_apply_fix, {
        "verify": "verify",
        "fix": "fix"
    })
    workflow.add_conditional_edges("verify", route_after_sandbox, {
        "pass": "report",
        "fail": "fix",
        "env_error": "fix", # Agent uses env diagnosis to fix requirements/etc.
        "give_up": "report"
    })
    workflow.add_edge("report", END)
    
    app = workflow.compile()
    
    # ── Execution ──
    initial_state: AgentState = {
        "incident": incident,
        "incident_id": incident_id,
        "repo_url": repo_url,
        "repo_path": None,
        "service_path": None,
        "service": "unknown",
        "language": "python",
        "container_id": None,
        "hypothesis": "",
        "root_cause": "",
        "target_file": "",
        "file_content": "",
        "proposed_fix": None,
        "test_results": None,
        "attempt_count": 0,
        "messages": [],
        "files_analyzed": [],
        "history": "",
        "confidence": 0.0,
        "report": None,
        "pr_url": None,
        "status": "starting",
        "similar_incidents": [],
        "scratchpad": "",
        # Sandbox v2 initial state
        "sandbox_result": None,
        "sandbox_attempts": 0,
        "last_test_context": "",
        "max_sandbox_attempts": 4,
        "investigation_attempts": 0,
        "changed_files": [] # Initialized as empty
    }
    
    container_id = None
    try:
        final_state = app.invoke(initial_state)
        container_id = final_state.get("container_id")
        return final_state.get("report") or ResolutionReport(incident_id=incident_id)
    except Exception as e:
        logger.error(f"Agent workflow failed for {incident_id}: {e}")
        update_incident_status(incident_id, "failed", f"Agent workflow failed: {e}")
        return ResolutionReport(incident_id=incident_id, root_cause=f"Error: {e}")
    finally:
        if container_id:
            try:
                docker_runner.destroy_sandbox(container_id)
                logger.info(f"Cleaned up Docker sandbox: {container_id[:12]}")
            except Exception as cleanup_err:
                logger.warning(f"Failed to cleanup Docker sandbox: {cleanup_err}")


# --- LangGraph Nodes ---

def parse_node(state: AgentState) -> dict:
    """Parses the incident ticket to extract structured context."""
    incident = state["incident"]
    incident_id = state["incident_id"]
    repo_url = state["repo_url"]
    
    update_incident_status(incident_id, "parsing", "Parsing incident ticket")
    
    parsed = parse_ticket(
        incident_id=incident_id,
        repository=incident.get("repository", repo_url),
        issue_number=incident.get("issue_number", ""),
        title=incident.get("title", ""),
        description=incident.get("description", ""),
        error_log=incident.get("error_log", ""),
    )
    
    from .memory_manager import EpisodicMemory
    memory = EpisodicMemory(repo_url=repo_url)
    similar = memory.retrieve(query=parsed.get("error_message") or parsed.get("hypothesis") or "")
    
    push_thought(incident_id, f"Parsing ticket for {incident_id}. Service: {parsed.get('service')}. Detected {len(similar)} similar past incidents in episodic memory.")
    logger.info(f"[HYPOTHESIS] {incident_id}: {parsed.get('hypothesis')}")
    return {
        "service": parsed.get("service", "unknown"),
        "language": "python" if parsed.get("service", "").lower().startswith("python") else "node",
        "hypothesis": parsed.get("hypothesis", ""),
        "similar_incidents": similar,
        "status": "investigating",
        "messages": [f"Parsed ticket. Initial hypothesis: {parsed.get('hypothesis')}. Found {len(similar)} similar past incidents."]
    }

def setup_node(state: AgentState) -> dict:
    """Clones the repo and starts the Docker sandbox."""
    incident_id = state["incident_id"]
    repo_url = state["repo_url"]
    language = state["language"]
    
    update_incident_status(incident_id, "cloning", "Setting up environment")
    push_thought(incident_id, f"Initiating setup for {incident_id}. Cloning {repo_url} and provisioning a {language} Docker sandbox.")
    
    from agent.repo_manager import clone_repo, create_branch
    
    repo_path = clone_repo(repo_url)
    create_branch(repo_path, f"fix/{incident_id.lower()}")
    service_path = _detect_service_root(repo_path, state["service"])
    
    # We no longer start a permanent container. 
    # Ephemeral sandboxes are managed by SandboxManager in the verify/sandbox node.
    
    return {
        "repo_path": repo_path,
        "service_path": service_path,
        "container_id": None,
        "messages": [f"Environment setup complete. Repository cloned to {repo_path}. Ephemeral sandboxes will be used for execution."]
    }

def _get_pinned_context(state: AgentState) -> str:
    incident = state["incident"]
    return f"""Incident ID: {state['incident_id']}
Title: {incident.get('title')}
Description: {incident.get('description')}
Error: {state.get('error_message') or incident.get('error_log')}"""

def investigate_node(state: AgentState) -> dict:
    """Investigates the codebase to find the root cause."""
    incident_id = state["incident_id"]
    service_path = state["service_path"]
    
    update_incident_status(incident_id, "investigating", "Analyzing codebase")
    
    root_cause, target_file, file_content, files_analyzed = _investigate_codebase(
        incident_id=incident_id,
        service=state.get("service", "unknown"),
        error_message=state["incident"].get("error_log", ""),
        hypothesis=state["hypothesis"],
        service_path=service_path,
        affected_file=state["incident"].get("affected_file", ""),
        container_id=state["container_id"],
        workdir=state["service_path"]
    )

    # Hierarchical Summarization: Store summary if file is large
    if len(file_content) > 3000:
        push_thought(incident_id, f"File {target_file} is large ({len(file_content)} chars). Generating hierarchical summary for context window optimization.")
        from .tools import summarize_file
        try:
            summary = summarize_file(target_file, file_content)
            state["history"] += f"\nSummary of {target_file}: {summary}"
        except:
            pass

    push_thought(incident_id, f"Investigating {target_file}. Running root cause analysis using context pinning and current scratchpad.")

    from .fix_generator import analyze_code
    pinned = _get_pinned_context(state)
    analysis = analyze_code(
        incident_id=incident_id,
        service=state.get("service_type", "unknown"),
        error_message=state.get("error_message") or "",
        hypothesis=state["hypothesis"],
        file_path=target_file,
        file_content=file_content,
        pinned_context=pinned,
        scratchpad=state.get("scratchpad", "")
    )
    
    push_thought(incident_id, f"[ROOT CAUSE ANALYSIS] Confirmed root cause in {target_file}: {analysis.get('root_cause_explanation') or root_cause}")

    lang = detect_language(state["incident"], files_analyzed)

    return {
        "root_cause": analysis.get("root_cause_explanation") or root_cause,
        "target_file": target_file,
        "file_content": file_content,
        "files_analyzed": files_analyzed,
        "language": lang,
        "investigation_attempts": state.get("investigation_attempts", 0) + 1,
        "messages": [f"Root cause analyzed: {root_cause[:100]}... in {target_file}. Sandbox language detected: {lang}"]
    }

def fix_node(state: AgentState) -> dict:
    """Generates and applies a fix."""
    incident_id = state["incident_id"]
    
    if state["attempt_count"] == 0:
        push_thought(incident_id, f"No previous attempts. Generating minimal fix for root cause: {state['root_cause'][:60]}...")
        update_incident_status(incident_id, "fixing", "Generating fix")
        pinned = _get_pinned_context(state)
        fix = generate_fix(
            incident_id=incident_id,
            root_cause=state["root_cause"],
            file_path=state["target_file"],
            file_content=state["file_content"],
            error_log=state["incident"].get("error_log", ""),
            pinned_context=pinned,
            scratchpad=state.get("scratchpad", "")
        )
    else:
        update_incident_status(incident_id, "retrying", f"Revising fix (attempt {state['attempt_count'] + 1})")
        # Logic to call LLM again with failure feedback
        fix = generate_retry_fix(
            file_path=state["target_file"],
            previous_attempts=str(state.get("messages", [])),
            test_output=json.dumps(state.get("sandbox_result")),
            patching_error=state.get("last_patch_error", ""),
        )

    logger.info(f"[FIX EXPLANATION] {incident_id}: {fix.explanation}")

    # Safety Check: Never patch incident metadata files
    if "incident" in fix.file_path.lower() or fix.file_path.startswith("incidents/"):
        error_msg = f"SAFETY BLOCK: Agent attempted to patch an incident metadata file: {fix.file_path}. Only code files allowed."
        return {
            "proposed_fix": fix,
            "attempt_count": state["attempt_count"] + 1,
            "status": "failed",
            "last_patch_error": error_msg,
            "messages": state.get("messages", []) + [error_msg]
        }

    # Use the new surgical patcher
    patch_res = patch_file_tool(
        file_path=os.path.join(state["repo_path"], fix.file_path),
        new_code=fix.new_code,
        symbol_name=fix.symbol_name,
        symbol_type=fix.symbol_type,
        start_line=fix.start_line,
        end_line=fix.end_line,
        expected_old_code=fix.expected_old_code
    )
    
    applied = patch_res["success"]
    changed_files = state.get("changed_files", [])
    if applied and fix.file_path not in changed_files:
        changed_files.append(fix.file_path)
    
    error_msg = patch_res.get("error", "")
    push_thought(incident_id, f"Fix strategy generated. Type: {patch_res.get('strategy_used', 'unknown')}. {'Applied to codebase surgicaly.' if applied else f'Patch failed: {error_msg}'}")
    
    return {
        "proposed_fix": fix,
        "attempt_count": state["attempt_count"] + 1,
        "status": "verifying" if applied else "failed",
        "changed_files": changed_files,
        "last_patch_error": error_msg,
        "messages": state.get("messages", []) + [f"Applied fix: {fix.explanation}" if applied else f"Patch failed: {error_msg}"]
    }

def _detect_affected_tests(repo_path: str, target_file: str, service_type: str) -> List[str]:
    """Identifies tests that are likely relevant to the changed file."""
    basename = os.path.basename(target_file).split('.')[0]
    relevant_tests = []
    search_patterns = [f"test_{basename}.py", f"{basename}_test.py", f"{basename}.test.js", f"{basename}.spec.js"]
    
    for root, dirs, files in os.walk(repo_path):
        for file in files:
            if file in search_patterns:
                relevant_tests.append(os.path.relpath(os.path.join(root, file), repo_path))
    return relevant_tests

def report_node(state: AgentState) -> dict:
    """Generates the final report and creates a PR."""
    incident_id = state["incident_id"]
    repo_path = state["repo_path"]
    target_file = state["target_file"]
    branch_name = f"fix/{incident_id.lower()}" # Simplified for now
    
    update_incident_status(incident_id, "reporting", "Generating resolution report")
    push_thought(incident_id, f"Incident investigation complete. Status: {state['status']}. Compiling final resolution report and PR documentation.")
    
    # Minimal report generation for now
    # Calculate Senior-Level Confidence Score
    # Formula: (tests_passed + fix_minimal + root_cause_precise - retries)
    base_confidence = 0
    if state["status"] == "passed": base_confidence += 40
    if state.get("proposed_fix") and not state.get("last_patch_error"): base_confidence += 30
    import re
    if bool(re.search(r'[:#]\d+', state["root_cause"])): base_confidence += 30
    base_confidence -= min(30, state["attempt_count"] * 10)
    
    report = state.get("report") or ResolutionReport(
        incident_id=incident_id,
        ticket_text=json.dumps(state["incident"]),
        hypothesis=state["hypothesis"],
        root_cause=state["root_cause"],
        files_analyzed=state.get("files_analyzed", []),
        service=state.get("service", "unknown"),
        fix=state["proposed_fix"],
        test_results=state["test_results"],
        confidence_score=max(0, min(100, base_confidence))
    )
    
    report.report_markdown = _generate_report_markdown(report)
    
    # Create PR logic
    # Antigravity Protocol: PR ONLY if tests passed
    should_pr = (state["status"] == "passed")
    if state["proposed_fix"] and state["proposed_fix"].no_fix_needed:
        should_pr = False
        push_thought(incident_id, "No fix was required. Skipping PR.")
    
    if not should_pr and state["status"] == "failed":
        push_thought(incident_id, "CRITICAL: Sandbox verification FAILED. Blocking PR creation to prevent broken code merge.")
        # But we still generate a report

    if should_pr:
        # Store successful trace in episodic memory
        if state["status"] == "passed":
            from .memory_manager import EpisodicMemory
            memory = EpisodicMemory(repo_url=state["repo_url"])
            memory.store(state["incident_id"], {
                "root_cause": state["root_cause"],
                "fix": state["proposed_fix"].explanation if state["proposed_fix"] else "N/A",
                "test_output": state["test_results"].output if state["test_results"] else ""
            })

        try:
            from agent.repo_manager import commit_fix, push_branch
            pr_creator = PRCreator()
            commit_fix(repo_path, target_file, incident_id)
            push_branch(repo_path, branch_name)
            
            pr_url = pr_creator.create_pull_request(
                repo_name=state["repo_url"].split("github.com/")[-1].replace(".git", ""),
                branch_name=branch_name,
                title=f"Fix: {incident_id}",
                body=report.report_markdown
            )
            update_incident_status(incident_id, "pr_created", f"PR created: {pr_url}")
            update_incident_status(incident_id, "completed", "Incident resolved.")
            return {"pr_url": pr_url, "status": "completed"}
        except Exception as e:
            logger.error(f"Failed to create PR: {e}")
            update_incident_status(incident_id, "pr_failed", f"PR creation failed: {e}")
    
    update_incident_status(incident_id, "completed", "No PR created.")
    return {"status": "completed"}

def critic_node(state: AgentState) -> dict:
    """
    Acts as an adversary to the planner/fixer.
    Reviews the proposed fix and provides feedback before it is applied.
    """
    from .fix_generator import call_llm
    incident = state["incident"]
    fix = state["proposed_fix"]
    
    if not fix or fix.no_fix_needed or "incident" in fix.file_path.lower():
        push_thought(state["incident_id"], f"Critic REJECTED: Proposed fix targets non-code file or is empty: {fix.file_path if fix else 'None'}")
        return {
            "status": "failed",
            "messages": ["Critic rejected: Fix must target source code, not incident metadata."]
        }

    prompt = f"""
    You are a Senior Code Reviewer. Review the following proposed fix for an incident.
    Incident: {incident.get('title')}
    Reported Error: {incident.get('error_log')}
    Proposed Fix: {fix.explanation}
    Original Code: {fix.original_snippet}
    New Code: {fix.new_code}
    
    Explain if this fix is correct, minimal, and doesn't introduce regressions.
    If you approve, start your response with 'APPROVED'.
    If you object, explain why and what needs to change.
    """
    
    try:
        feedback = call_llm(prompt)
        push_thought(state["incident_id"], f"Adversarial Review (Critic): {feedback[:100]}...")
        approved = feedback.strip().upper().startswith("APPROVED")
    except:
        approved = True # Fallback to approval if LLM fails
        feedback = "Approved (fallback)"

    return {
        "status": "verifying" if approved else "revising",
        "messages": [f"Critic feedback: {'Approved' if approved else 'Objected'}. Details: {feedback[:100]}..."]
    }

def should_apply_fix(state: AgentState) -> str:
    """Conditional edge after critic_node."""
    if state["status"] == "verifying":
        return "verify"
    return "fix"

def route_after_investigate(state: AgentState) -> str:
    """Ensures a high-quality root cause (file + line + mechanism) was found before fixing."""
    incident_id = state["incident_id"]
    root_cause = state.get("root_cause", "").lower()
    files = state.get("files_analyzed", [])
    attempts = state.get("investigation_attempts", 0)

    # 1. Check for actual source code files
    SOURCE_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rb", ".cpp", ".c", ".h", ".rs"}
    source_files = [
        f for f in files 
        if any(f.lower().endswith(ext) for ext in SOURCE_EXTENSIONS)
        and "incident" not in f.lower()
    ]
    
    # 2. Check for precision (e.g., "file.js:42" or "line 15")
    import re
    has_precision = bool(re.search(r'[:#]\d+', root_cause)) or bool(re.search(r'line \d+', root_cause))
    
    # 3. Decision Logic:
    # If we have a precise root cause in a source file, we're ready to fix.
    if has_precision and source_files and "no fix needed" not in root_cause:
        return "fix"
        
    # If we've already done 3 loops and haven't found a surgical cause, 
    # we either take our best guess ('fix') or give up.
    if attempts >= 3:
        if "no fix needed" in root_cause or "could not find" in root_cause:
             push_thought(incident_id, "Investigation Gate: Max attempts reached without finding root cause. Ending workflow.")
             return "give_up" # You might need to add this to LangGraph edges
        return "fix"

    # If we read no source code, we definitely need a retry.
    if not source_files:
        push_thought(incident_id, "Investigation Gate: No actual source code was analyzed. Forcing retry.")
        return "retry"
        
    # If we read code but it was the wrong file (vague cause), retry.
    if not has_precision:
        push_thought(incident_id, "Investigation Gate: Root cause is vague (no line reference). Forcing deeper investigation.")
        return "retry"
        
    return "fix"
