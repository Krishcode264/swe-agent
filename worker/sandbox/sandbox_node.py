"""
sandbox_node.py

The LangGraph node that the agent calls to run its fix through the sandbox.
This is the single interface the agent graph talks to — it hides all the
Docker/parsing complexity behind a clean state update.

Plug into your agent graph:
    graph.add_node("sandbox", sandbox_node)
    graph.add_edge("tool_executor", "sandbox")
    graph.add_conditional_edges(
        "sandbox",
        route_after_sandbox,
        {"pass": "pr_builder", "fail": "planner", "env_error": "planner"},
    )
"""

from __future__ import annotations

import logging
from typing import Optional

import anthropic

from .sandbox_manager import SandboxConfig, SandboxManager
from .test_runner import SandboxTestRunner, TestRunResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Agent state (matches your LangGraph AgentState TypedDict)
# ---------------------------------------------------------------------------
# Add these fields to your existing AgentState:
#
# class AgentState(TypedDict):
#     ...existing fields...
#     sandbox_result:    Optional[dict]     # structured TestRunResult as dict
#     sandbox_attempts:  int                # how many sandbox runs so far
#     last_test_context: str                # what the agent sees after a run


# ---------------------------------------------------------------------------
# The node function
# ---------------------------------------------------------------------------

def sandbox_node(state: dict) -> dict:
    """
    LangGraph node: run the current patched repo through the sandbox.

    Reads from state:
        repo_path, incident_id, language, changed_files

    Writes to state:
        sandbox_result      — structured dict the agent reasons over
        last_test_context   — compact string injected into next LLM call
        sandbox_attempts    — incremented each call
        confidence_score    — updated from test results
        messages            — appends the test result as a tool_result message
    """
    repo_path   = state.get("repo_path", "")
    incident_id = state.get("incident_id", "unknown")
    language    = state.get("language", "python")
    changed_files = state.get("changed_files", [])
    attempt     = state.get("sandbox_attempts", 0) + 1

    logger.info("Sandbox run #%d for incident %s", attempt, incident_id)

    # Build config
    config = SandboxConfig(
        repo_path   = repo_path,
        incident_id = incident_id,
        language    = language,
        # Tighten limits on retry attempts (already know it's not env issues)
        timeout_test = 180 if attempt == 1 else 120,
        # Run full suite on first attempt; incremental after that
    )

    llm_client = anthropic.Anthropic()  # for env error advice
    runner     = SandboxTestRunner(language=language, llm_client=llm_client)
    manager    = SandboxManager(config)

    try:
        with manager.container() as sandbox:
            result: TestRunResult = runner.run(
                sandbox,
                changed_files = changed_files,
                run_all       = (attempt == 1),   # full suite on first run
            )
    except Exception as exc:
        logger.error("Sandbox failed to execute: %s", exc)
        result = _make_error_result(str(exc))

    # Compact context string the LLM will see
    context = result.to_agent_context()

    # Append as a "tool_result" message so the agent sees it in conversation
    messages = state.get("messages", [])
    messages.append({
        "role": "user",
        "content": [{
            "type": "text",
            "text": f"[sandbox result — attempt {attempt}]\n\n{context}",
        }],
    })

    return {
        **state,
        "sandbox_result":    _result_to_dict(result),
        "last_test_context": context,
        "sandbox_attempts":  attempt,
        "confidence_score":  result.confidence_score,
        "messages":          messages,
    }


# ---------------------------------------------------------------------------
# Routing function — used by LangGraph conditional edges
# ---------------------------------------------------------------------------

def route_after_sandbox(state: dict) -> str:
    """
    Decides what happens after a sandbox run.

    Returns:
        "pass"      → go to pr_builder
        "fail"      → go back to planner (agent revises the fix)
        "env_error" → go back to planner with env error context
        "give_up"   → max attempts reached, mark incident as failed
    """
    result_dict = state.get("sandbox_result", {})
    attempts    = state.get("sandbox_attempts", 0)
    max_attempts = state.get("max_sandbox_attempts", 4)

    if attempts >= max_attempts:
        logger.warning("Max sandbox attempts reached (%d), giving up", attempts)
        return "give_up"

    env_errors = result_dict.get("env_errors", [])
    all_passed = result_dict.get("all_passed", False)

    if all_passed:
        return "pass"
    if env_errors:
        return "env_error"
    return "fail"


# ---------------------------------------------------------------------------
# Utility: convert TestRunResult to plain dict for state storage
# ---------------------------------------------------------------------------

def _result_to_dict(result: TestRunResult) -> dict:
    return {
        "passed":       result.passed,
        "failed":       result.failed,
        "errors":       result.errors,
        "skipped":      result.skipped,
        "total":        result.total,
        "all_passed":   result.all_passed,
        "confidence":   result.confidence_score,
        "duration_s":   result.duration_s,
        "env_errors":   [
            {"category": e.category, "raw_error": e.raw_error, "suggestion": e.suggestion}
            for e in result.env_errors
        ],
        "failing_tests": [
            {
                "name":       t.name,
                "status":     t.status,
                "error_type": t.error_type,
                "error_msg":  t.error_msg,
                "file":       t.file,
                "line":       t.line,
            }
            for t in result.test_cases
            if t.status in ("failed", "error")
        ],
        "quality": [
            {"tool": q.tool, "passed": q.passed, "issues": q.issues[:5]}
            for q in result.quality
        ],
        "coverage_pct": result.coverage_pct,
    }


def _make_error_result(error_msg: str) -> TestRunResult:
    from .test_runner import TestRunResult, EnvError
    r = TestRunResult()
    r.env_errors = [EnvError(category="env_config", raw_error=error_msg)]
    return r


# ---------------------------------------------------------------------------
# LangGraph wiring example (paste into your agent_graph.py)
# ---------------------------------------------------------------------------

GRAPH_WIRING_EXAMPLE = '''
from langgraph.graph import StateGraph, END
from sandbox_node import sandbox_node, route_after_sandbox

def build_agent_graph():
    graph = StateGraph(AgentState)

    graph.add_node("planner",      planner_node)
    graph.add_node("tool_executor", tool_executor_node)
    graph.add_node("critic",       critic_node)
    graph.add_node("sandbox",      sandbox_node)
    graph.add_node("pr_builder",   pr_builder_node)
    graph.add_node("failed",       mark_failed_node)

    graph.set_entry_point("planner")

    graph.add_edge("planner",       "tool_executor")
    graph.add_edge("tool_executor", "critic")
    graph.add_edge("critic",        "sandbox")

    graph.add_conditional_edges(
        "sandbox",
        route_after_sandbox,
        {
            "pass":      "pr_builder",
            "fail":      "planner",     # re-plan with test failure context
            "env_error": "planner",     # re-plan with env fix suggestion
            "give_up":   "failed",
        },
    )

    graph.add_edge("pr_builder", END)
    graph.add_edge("failed",     END)

    return graph.compile()
'''