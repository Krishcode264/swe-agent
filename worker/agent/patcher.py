"""
patcher.py — Production-grade file patching for AI agents.

Replaces naive text matching with a three-tier cascade:
  1. AST node replace  (tree-sitter, surgical byte-range edit)
  2. Line range replace (precise, indentation-aware)
  3. Full function rewrite (LLM rewrites entire function, spliced back in)

Never use raw string find/replace in production agents.
"""

from __future__ import annotations

import re
import textwrap
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

# tree-sitter: `pip install tree-sitter tree-sitter-python tree-sitter-javascript`
try:
    import tree_sitter_python as tspython
    import tree_sitter_javascript as tsjavascript
    from tree_sitter import Language, Parser, Node
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class PatchStrategy(str, Enum):
    AST_NODE    = "ast_node"      # surgical: replace an AST-identified node
    LINE_RANGE  = "line_range"    # replace lines N through M
    FULL_REWRITE = "full_rewrite" # LLM rewrote the entire function; splice in
    TEXT_REPLACE = "text_replace" # fallback: literal snippet replacement


@dataclass
class PatchRequest:
    """
    Everything the agent needs to specify a change.
    Provide as much as you know; the patcher uses the most precise
    strategy available given what's filled in.
    """
    file_path: str

    # Strategy hint (patcher will validate and fall back if needed)
    strategy: Optional[PatchStrategy] = None

    # AST-level targeting (most precise)
    symbol_name:  Optional[str] = None   # e.g. "verify_token", "UserService.validate"
    symbol_type:  Optional[str] = None   # "function", "method", "class"

    # Line-range targeting (fallback)
    start_line: Optional[int] = None     # 1-indexed, inclusive
    end_line:   Optional[int] = None     # 1-indexed, inclusive

    # The new content to write
    new_code: str = ""

    # Context for validation
    expected_old_code: Optional[str] = None  # used to verify we found the right node


@dataclass
class PatchResult:
    success: bool
    strategy_used: PatchStrategy
    file_path: str
    lines_changed: tuple[int, int]   # (start, end) of replaced range
    backup_path: Optional[str] = None
    error: Optional[str] = None
    diff_summary: Optional[str] = None


# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------

def _detect_language(file_path: str) -> Optional[str]:
    ext = Path(file_path).suffix.lower()
    return {
        ".py":  "python",
        ".js":  "javascript",
        ".ts":  "javascript",   # ts-sitter js parser handles tsx/ts well enough
        ".jsx": "javascript",
        ".tsx": "javascript",
    }.get(ext)


# ---------------------------------------------------------------------------
# Tree-sitter helpers
# ---------------------------------------------------------------------------

def _get_parser(language: str) -> Optional["Parser"]:
    if not TREE_SITTER_AVAILABLE:
        return None
    try:
        if language == "python":
            lang = Language(tspython.language())
        elif language == "javascript":
            lang = Language(tsjavascript.language())
        else:
            return None
        parser = Parser(lang)
        return parser
    except Exception:
        return None


def _find_node_by_name(
    root: "Node",
    symbol_name: str,
    symbol_type: Optional[str],
    source_bytes: bytes,
) -> Optional["Node"]:
    """
    Walk the AST and return the node whose name matches symbol_name.
    symbol_type filters by node kind ("function_definition", "class_definition", etc.)
    """
    type_map = {
        "function": {"function_definition", "function_declaration", "method_definition"},
        "method":   {"function_definition", "function_declaration", "method_definition"},
        "class":    {"class_definition", "class_declaration"},
        None:       None,  # match any kind
    }
    allowed_kinds = type_map.get(symbol_type)

    def _walk(node: "Node") -> Optional["Node"]:
        if allowed_kinds is None or node.type in allowed_kinds:
            # Check if this node has a "name" child whose text matches
            for child in node.children:
                if child.type in ("identifier", "property_identifier"):
                    name = source_bytes[child.start_byte:child.end_byte].decode("utf-8")
                    if name == symbol_name:
                        return node
        for child in node.children:
            result = _walk(child)
            if result is not None:
                return result
        return None

    # Handle "Class.method" notation
    if "." in symbol_name:
        class_name, method_name = symbol_name.split(".", 1)
        class_node = _find_node_by_name(root, class_name, "class", source_bytes)
        if class_node:
            return _find_node_by_name(class_node, method_name, "method", source_bytes)
        return None

    return _walk(root)


# ---------------------------------------------------------------------------
# Strategy 1: AST node replace
# ---------------------------------------------------------------------------

def _patch_ast_node(
    source: str,
    request: PatchRequest,
    language: str,
) -> Optional[tuple[str, tuple[int, int]]]:
    """
    Locate the target symbol using tree-sitter, replace its source range.
    Returns (new_source, (start_line, end_line)) or None if not found.
    """
    parser = _get_parser(language)
    if parser is None:
        return None

    source_bytes = source.encode("utf-8")
    tree = parser.parse(source_bytes)
    node = _find_node_by_name(
        tree.root_node,
        request.symbol_name,
        request.symbol_type,
        source_bytes,
    )
    if node is None:
        return None

    # Optional sanity check: does the node's text approximately match what the
    # agent expected? Catches cases where the wrong overload was found.
    if request.expected_old_code:
        node_text = source_bytes[node.start_byte:node.end_byte].decode("utf-8")
        if not _fuzzy_match(node_text, request.expected_old_code, threshold=0.6):
            return None

    # Preserve leading indentation of the original node
    start_line = node.start_point[0]   # 0-indexed
    end_line   = node.end_point[0]     # 0-indexed

    # Detect indentation of the original symbol's line
    lines = source.splitlines(keepends=True)
    original_indent = _detect_indent(lines[start_line])

    # Re-indent the new code to match
    new_code_reindented = _reindent(request.new_code, original_indent)

    # Splice using byte offsets (tree-sitter offsets are bytes)
    source_bytes = source.encode("utf-8")
    new_source_bytes = (
        source_bytes[:node.start_byte]
        + new_code_reindented.encode("utf-8")
        + source_bytes[node.end_byte:]
    )
    return new_source_bytes.decode("utf-8"), (start_line + 1, end_line + 1)


# ---------------------------------------------------------------------------
# Strategy 2: Line range replace
# ---------------------------------------------------------------------------

def _patch_line_range(
    source: str,
    request: PatchRequest,
) -> Optional[tuple[str, tuple[int, int]]]:
    """
    Replace lines [start_line, end_line] (1-indexed, inclusive) with new_code.
    Preserves indentation of first replaced line.
    """
    if request.start_line is None or request.end_line is None:
        return None

    lines = source.splitlines(keepends=True)
    total = len(lines)

    s = request.start_line - 1   # convert to 0-indexed
    e = request.end_line          # slice end is exclusive, so no -1

    if s < 0 or e > total or s >= e:
        return None

    # Preserve original indentation
    original_indent = _detect_indent(lines[s])
    new_code_reindented = _reindent(request.new_code, original_indent)

    # Ensure trailing newline
    if not new_code_reindented.endswith("\n"):
        new_code_reindented += "\n"

    new_lines = lines[:s] + [new_code_reindented] + lines[e:]
    return "".join(new_lines), (request.start_line, request.end_line)


# ---------------------------------------------------------------------------
# Strategy 3: Full function rewrite (LLM already produced complete function)
# ---------------------------------------------------------------------------

def _patch_full_rewrite(
    source: str,
    request: PatchRequest,
    language: str,
) -> Optional[tuple[str, tuple[int, int]]]:
    """
    Agent provides a fully rewritten function. We locate the old one via AST
    (or line range), rip it out entirely, and splice in the new version.
    This is effectively AST node replace but expects the entire function body,
    not just a sub-expression.
    """
    # Try AST first if symbol name is available
    if request.symbol_name and TREE_SITTER_AVAILABLE:
        result = _patch_ast_node(source, request, language)
        if result:
            return result

    # Fall back to line range
    if request.start_line and request.end_line:
        return _patch_line_range(source, request)

    return None


# ---------------------------------------------------------------------------
# Strategy 4: Text Replace (Fallback of last resort)
# ---------------------------------------------------------------------------

def _patch_text_replace(
    source: str,
    request: PatchRequest,
) -> Optional[tuple[str, tuple[int, int]]]:
    """
    Final fallback: search for original_snippet and replace with new_code.
    This is naive but handles cases where AST and line ranges fail.
    """
    if not request.original_snippet:
        return None

    if request.original_snippet in source:
        # Detected indentation of the first line of the snippet
        lines = source.splitlines(keepends=True)
        start_byte = source.find(request.original_snippet)
        start_line = source[:start_byte].count("\n")
        
        orig_lines = request.original_snippet.splitlines()
        original_indent = _detect_indent(orig_lines[0]) if orig_lines else ""
        new_code_reindented = _reindent(request.new_code, original_indent)

        new_source = source.replace(request.original_snippet, new_code_reindented, 1)
        
        end_line = start_line + len(orig_lines)
        return new_source, (start_line + 1, end_line)

    return None


# ---------------------------------------------------------------------------
# Main cascade entry point
# ---------------------------------------------------------------------------

def apply_patch(request: PatchRequest) -> PatchResult:
    """
    Apply a patch using the best available strategy, cascading through
    fallbacks automatically. Creates a .bak backup before modifying.
    """
    path = Path(request.file_path)
    if not path.exists():
        return PatchResult(
            success=False,
            strategy_used=PatchStrategy.LINE_RANGE,
            file_path=request.file_path,
            lines_changed=(0, 0),
            error=f"File not found: {request.file_path}",
        )

    source = path.read_text(encoding="utf-8")
    language = _detect_language(request.file_path)

    # Backup
    backup_path = str(path) + ".bak"
    Path(backup_path).write_text(source, encoding="utf-8")

    result_data: Optional[tuple[str, tuple[int, int]]] = None
    strategy_used = PatchStrategy.LINE_RANGE

    # ---- Cascade ----
    # Tier 1: AST node replace
    if (
        TREE_SITTER_AVAILABLE
        and language
        and request.symbol_name
        and request.strategy in (None, PatchStrategy.AST_NODE)
    ):
        result_data = _patch_ast_node(source, request, language)
        if result_data:
            strategy_used = PatchStrategy.AST_NODE

    # Tier 2: Full rewrite (uses AST + line range internally)
    if result_data is None and request.strategy == PatchStrategy.FULL_REWRITE:
        result_data = _patch_full_rewrite(source, request, language or "")
        if result_data:
            strategy_used = PatchStrategy.FULL_REWRITE

    # Tier 3: Line range
    if result_data is None and request.start_line and request.end_line:
        result_data = _patch_line_range(source, request)
        if result_data:
            strategy_used = PatchStrategy.LINE_RANGE

    if result_data is None:
        return PatchResult(
            success=False,
            strategy_used=strategy_used,
            file_path=request.file_path,
            lines_changed=(0, 0),
            backup_path=backup_path,
            error=(
                "All patch strategies failed. "
                "Provide either symbol_name (for AST) or start_line+end_line (for line range)."
            ),
        )

    new_source, lines_changed = result_data

    # Validate: new source must be parseable (for supported languages)
    if language and TREE_SITTER_AVAILABLE:
        if not _validate_syntax(new_source, language):
            return PatchResult(
                success=False,
                strategy_used=strategy_used,
                file_path=request.file_path,
                lines_changed=lines_changed,
                backup_path=backup_path,
                error="Patch produced a syntax error. Original file preserved.",
            )

    path.write_text(new_source, encoding="utf-8")

    diff_summary = _make_diff_summary(source, new_source, lines_changed)

    return PatchResult(
        success=True,
        strategy_used=strategy_used,
        file_path=request.file_path,
        lines_changed=lines_changed,
        backup_path=backup_path,
        diff_summary=diff_summary,
    )


# ---------------------------------------------------------------------------
# Agent-facing tool wrapper (plug this into your tool registry)
# ---------------------------------------------------------------------------

def patch_file_tool(
    file_path: str,
    new_code: str,
    symbol_name: Optional[str] = None,
    symbol_type: Optional[str] = None,
    start_line: Optional[int] = None,
    end_line: Optional[int] = None,
    expected_old_code: Optional[str] = None,
) -> dict:
    """
    Drop-in tool for your LangGraph tool executor node.

    The LLM should provide:
      - file_path: always
      - symbol_name + symbol_type: preferred (AST-level precision)
      - start_line + end_line: fallback (line range)
      - expected_old_code: optional safety check
      - new_code: the replacement content

    Returns a dict the agent can reason over.
    """
    # Infer strategy from what was provided
    if symbol_name:
        strategy = PatchStrategy.AST_NODE
    elif start_line and end_line:
        strategy = PatchStrategy.LINE_RANGE
    else:
        strategy = None

    request = PatchRequest(
        file_path=file_path,
        strategy=strategy,
        symbol_name=symbol_name,
        symbol_type=symbol_type,
        start_line=start_line,
        end_line=end_line,
        new_code=new_code,
        expected_old_code=expected_old_code,
    )

    result = apply_patch(request)

    return {
        "success": result.success,
        "strategy_used": result.strategy_used.value if result.strategy_used else None,
        "lines_changed": result.lines_changed,
        "diff_summary": result.diff_summary,
        "error": result.error,
        "backup_path": result.backup_path,
    }


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _detect_indent(line: str) -> str:
    """Return leading whitespace of a line."""
    return line[: len(line) - len(line.lstrip())]


def _reindent(code: str, target_indent: str) -> str:
    """
    Normalise the indentation of new_code to match target_indent.
    Strips the common leading whitespace from new_code first (dedent),
    then re-adds target_indent to every line.
    """
    dedented = textwrap.dedent(code)
    lines = dedented.splitlines(keepends=True)
    return "".join(
        (target_indent + line) if line.strip() else line
        for line in lines
    )


def _fuzzy_match(a: str, b: str, threshold: float = 0.7) -> bool:
    """
    Very lightweight similarity check — avoids pulling in difflib for
    a simple sanity gate. Checks character overlap ratio.
    """
    a_clean = re.sub(r"\s+", " ", a.strip())
    b_clean = re.sub(r"\s+", " ", b.strip())
    if not a_clean or not b_clean:
        return False
    shorter, longer = sorted([a_clean, b_clean], key=len)
    matches = sum(c in longer for c in shorter)
    return (matches / len(shorter)) >= threshold


def _validate_syntax(source: str, language: str) -> bool:
    """Parse with tree-sitter and return True if no ERROR nodes exist."""
    if not TREE_SITTER_AVAILABLE:
        return True  # can't validate, assume OK
    parser = _get_parser(language)
    if parser is None:
        return True
    tree = parser.parse(source.encode("utf-8"))
    return not _has_error_node(tree.root_node)


def _has_error_node(node: "Node") -> bool:
    if node.type == "ERROR":
        return True
    return any(_has_error_node(child) for child in node.children)


def _make_diff_summary(old: str, new: str, lines_changed: tuple[int, int]) -> str:
    old_lines = old.splitlines()
    new_lines = new.splitlines()
    removed = len(old_lines) - len(new_lines) + (lines_changed[1] - lines_changed[0] + 1)
    added   = new.count("\n") - old.count("\n") + removed
    return (
        f"Lines {lines_changed[0]}–{lines_changed[1]} replaced. "
        f"~{max(0,removed)} lines removed, ~{max(0,added)} lines added."
    )


# ---------------------------------------------------------------------------
# Quick smoke test (run directly: python patcher.py)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import tempfile, os

    SAMPLE = '''\
def greet(name: str) -> str:
    return "Hello " + name


def add(a: int, b: int) -> int:
    return a - b  # BUG: should be +


class Calculator:
    def multiply(self, x: int, y: int) -> int:
        return x + y  # BUG: should be *
'''

    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(SAMPLE)
        tmp = f.name

    print("=== Test 1: AST node replace (fix 'add' function) ===")
    r = patch_file_tool(
        file_path=tmp,
        symbol_name="add",
        symbol_type="function",
        new_code="def add(a: int, b: int) -> int:\n    return a + b  # fixed",
    )
    print(r)

    print("\n=== Test 2: AST node replace (fix Calculator.multiply) ===")
    r = patch_file_tool(
        file_path=tmp,
        symbol_name="Calculator.multiply",
        symbol_type="method",
        new_code="def multiply(self, x: int, y: int) -> int:\n    return x * y  # fixed",
    )
    print(r)

    print("\n=== Resulting file ===")
    print(Path(tmp).read_text())

    os.unlink(tmp)
    os.unlink(tmp + ".bak")