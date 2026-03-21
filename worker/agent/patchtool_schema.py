"""
patch_tool_schema.py

Defines:
  1. The tool schema the LLM sees (what it can call)
  2. The system prompt fragment that teaches it to use precise patching
  3. A response parser that extracts a PatchRequest from the LLM's tool call

Drop this into your LangGraph tool executor node.
"""

from __future__ import annotations
from typing import Any

# ---------------------------------------------------------------------------
# Tool schema (Anthropic / OpenAI tool-use format)
# ---------------------------------------------------------------------------

PATCH_FILE_TOOL_SCHEMA = {
    "name": "patch_file",
    "description": (
        "Apply a targeted code change to a file. "
        "Prefer symbol_name+symbol_type for surgical AST-level edits. "
        "Use start_line+end_line when you know the exact lines to replace. "
        "Always provide new_code — the complete replacement content for the target. "
        "Never use this to replace arbitrary text snippets; always target a named "
        "symbol or an explicit line range."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Relative path to the file to edit, from the repo root.",
            },
            "new_code": {
                "type": "string",
                "description": (
                    "The complete replacement code. "
                    "For function/method edits, include the full def line and body. "
                    "Do NOT include surrounding context — only the replacement node. "
                    "Indentation will be normalised automatically."
                ),
            },
            "symbol_name": {
                "type": "string",
                "description": (
                    "Name of the function, method, or class to replace. "
                    "For methods, use 'ClassName.method_name' notation. "
                    "Provide this whenever you know the symbol name — it's more "
                    "reliable than line numbers."
                ),
            },
            "symbol_type": {
                "type": "string",
                "enum": ["function", "method", "class"],
                "description": "Type of the symbol being replaced.",
            },
            "start_line": {
                "type": "integer",
                "description": (
                    "1-indexed line number where the replacement starts. "
                    "Use when you cannot target by symbol name "
                    "(e.g. fixing an import block, a decorator, a constant)."
                ),
            },
            "end_line": {
                "type": "integer",
                "description": "1-indexed line number where the replacement ends (inclusive).",
            },
            "expected_old_code": {
                "type": "string",
                "description": (
                    "Optional: a short excerpt of the code you expect to find at the "
                    "target location. Used as a sanity check — if the actual code "
                    "doesn't roughly match this, the patch is aborted. "
                    "Provide when you want an extra safety gate."
                ),
            },
        },
        "required": ["file_path", "new_code"],
    },
}


# ---------------------------------------------------------------------------
# Read file tool (agent needs to read with line numbers first)
# ---------------------------------------------------------------------------

READ_FILE_TOOL_SCHEMA = {
    "name": "read_file",
    "description": (
        "Read a file from the repository. Returns content with line numbers. "
        "Always read a file before patching it — you need the line numbers "
        "and exact current content."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Relative path to the file.",
            },
            "start_line": {
                "type": "integer",
                "description": "Optional: only return from this line (1-indexed).",
            },
            "end_line": {
                "type": "integer",
                "description": "Optional: only return up to this line (1-indexed).",
            },
        },
        "required": ["file_path"],
    },
}


# ---------------------------------------------------------------------------
# System prompt fragment — inject this into your agent's system prompt
# ---------------------------------------------------------------------------

PATCHING_SYSTEM_PROMPT = """
## How to make code changes

You have access to `patch_file` to modify code in the repository.
Follow these rules strictly — they prevent corrupting files.

### Always read before patching
Call `read_file` first. You need:
- Exact line numbers (the file might have changed since you last saw it)
- The correct symbol name as it appears in the file
- Confirmation that your understanding of the code is accurate

### Prefer symbol-level targeting
When fixing a function or method, always provide `symbol_name` and `symbol_type`.
This is more reliable than line numbers because:
- It survives unrelated edits elsewhere in the file
- It handles indentation automatically
- It finds the right node even if comments shifted the line count

Example — fixing a bug in a function:
```json
{
  "file_path": "auth/tokens.py",
  "symbol_name": "verify_token",
  "symbol_type": "function",
  "new_code": "def verify_token(token: str) -> User:\\n    payload = decode(token)\\n    if payload['exp'] >= time.time():\\n        raise TokenExpiredError()\\n    return User.from_payload(payload)",
  "expected_old_code": "if payload['exp'] > time.time()"
}
```

### Use line ranges for non-symbol targets
For imports, constants, decorators, or any code that isn't a named symbol,
use `start_line` + `end_line`.

Example — fixing a bad import on lines 3–4:
```json
{
  "file_path": "utils/helpers.py",
  "start_line": 3,
  "end_line": 4,
  "new_code": "from datetime import datetime, timezone\\nimport hashlib"
}
```

### new_code rules
- Include the COMPLETE replacement (full function def + body, or full line range)
- Do NOT include surrounding context lines — only what replaces the target
- Do NOT include line numbers in new_code
- Indentation is handled automatically — write at column 0, it will be re-indented

### What NOT to do
- Do not provide `old_code` and `new_code` as a text diff — there is no text-matching strategy
- Do not guess line numbers — read the file first and use the actual numbers
- Do not make multiple overlapping patches to the same file in one step —
  patch once, then re-read, then patch again if needed

### After patching
Always verify: call `read_file` on the changed region and confirm the new code
looks correct before running tests.
"""


# ---------------------------------------------------------------------------
# Tool implementations (plug these into your tool executor node)
# ---------------------------------------------------------------------------

import os
from pathlib import Path
from patcher import patch_file_tool   # from patcher.py in same package


def read_file_impl(file_path: str, start_line: int = None, end_line: int = None) -> dict:
    """
    Read a file, returning numbered lines so the agent can reference them.
    """
    path = Path(file_path)
    if not path.exists():
        return {"error": f"File not found: {file_path}"}

    lines = path.read_text(encoding="utf-8").splitlines()
    total = len(lines)

    s = (start_line - 1) if start_line else 0
    e = end_line if end_line else total

    s = max(0, min(s, total))
    e = max(0, min(e, total))

    numbered = "\n".join(
        f"{i + 1:4d}  {line}"
        for i, line in enumerate(lines[s:e], start=s)
    )

    return {
        "file_path": file_path,
        "total_lines": total,
        "shown_lines": f"{s+1}–{e}",
        "content": numbered,
    }


def dispatch_tool(tool_name: str, tool_input: dict[str, Any]) -> dict:
    """
    Route tool calls from the LangGraph tool executor node.
    Add this to your existing tool dispatch map.
    """
    if tool_name == "patch_file":
        return patch_file_tool(**tool_input)
    if tool_name == "read_file":
        return read_file_impl(**tool_input)
    raise ValueError(f"Unknown tool: {tool_name}")


# ---------------------------------------------------------------------------
# LangGraph node: tool executor
# Paste this into your agent_graph.py
# ---------------------------------------------------------------------------

TOOL_EXECUTOR_NODE_EXAMPLE = '''
from langgraph.graph import StateGraph
from langchain_anthropic import ChatAnthropic
from patch_tool_schema import PATCH_FILE_TOOL_SCHEMA, READ_FILE_TOOL_SCHEMA, dispatch_tool

def tool_executor_node(state: AgentState) -> AgentState:
    """
    Executes whatever tool the LLM called in the last message.
    Appends the tool result to state["messages"].
    """
    last_message = state["messages"][-1]

    # Anthropic SDK: tool_use blocks live in last_message.content
    tool_results = []
    for block in last_message.content:
        if block.type != "tool_use":
            continue
        result = dispatch_tool(block.name, block.input)
        tool_results.append({
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": str(result),
        })

    # Append results as a "user" message (Anthropic multi-turn tool format)
    state["messages"].append({"role": "user", "content": tool_results})
    return state
'''