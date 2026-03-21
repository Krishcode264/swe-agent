import os
import re
import shutil
import logging
from difflib import SequenceMatcher
from shared.models import Fix

logger = logging.getLogger(__name__)


def _normalize(text: str) -> str:
    """Collapse all whitespace (spaces, tabs, newlines) to single space, stripped."""
    return re.sub(r'\s+', ' ', text).strip()


def _strip_lines(text: str) -> list[str]:
    """Split into lines and strip each one."""
    return [ln.strip() for ln in text.splitlines()]


def apply_fix(repo_path: str, fix: Fix) -> bool:
    """
    Applies a code fix to a file within a repository using a tiered matching strategy.
    
    Tier 1: Exact string match
    Tier 2: Normalized whitespace match (collapsed spaces)
    Tier 3: Fuzzy line-by-line match using SequenceMatcher
    Tier 4: Key-line anchor match (find the most unique line from the snippet)

    Returns:
        True if the fix was applied successfully, False otherwise.
    """
    if fix.no_fix_needed:
        logger.info(f"Fix marked no_fix_needed — skipping file edit.")
        return False

    if not fix.original_snippet or not fix.original_snippet.strip():
        logger.warning(f"original_snippet is empty — cannot apply patch.")
        return False

    # Resolve the file path — try multiple bases since the LLM may return a path
    # relative to the service directory (e.g. app/routes/orders.py) or the repo root
    # (e.g. python-service/app/routes/orders.py) or an absolute path.
    full_path = fix.file_path
    if not os.path.isabs(full_path):
        # First: try relative to repo_path
        candidate = os.path.join(repo_path, fix.file_path.lstrip("/"))
        if os.path.exists(candidate):
            full_path = candidate
        else:
            full_path = candidate  # will fail below with a clear error

    if not os.path.exists(full_path):
        logger.error(f"File not found: {full_path}")
        return False

    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # ── Tier 1: Exact Match ──
        if fix.original_snippet in content:
            logger.info(f"Tier 1 (exact) match for {fix.file_path}")
            new_content = content.replace(fix.original_snippet, fix.new_code, 1)
            return _write_and_verify(full_path, new_content, fix.new_code)

        # ── Tier 2: Normalized Whitespace Match ──
        # Collapse all whitespace in both the file and the snippet, then locate
        norm_snippet = _normalize(fix.original_snippet)
        norm_content = _normalize(content)
        if norm_snippet in norm_content:
            logger.info(f"Tier 2 (normalized whitespace) match for {fix.file_path}")
            # Re-apply using line-aware replacement
            result = _replace_normalized(content, fix.original_snippet, fix.new_code)
            if result:
                return _write_and_verify(full_path, result, fix.new_code)

        # ── Tier 3: Fuzzy Line-by-Line Match ──
        snippet_lines = _strip_lines(fix.original_snippet)
        content_lines = content.splitlines()
        best_start, best_end, best_ratio = _find_best_block(snippet_lines, content_lines)

        if best_ratio >= 0.80:
            logger.info(f"Tier 3 (fuzzy line) match ratio={best_ratio:.2f} at lines {best_start}-{best_end}")
            prefix = '\n'.join(content_lines[:best_start])
            suffix = '\n'.join(content_lines[best_end:])
            new_content = (prefix + '\n' if prefix else '') + fix.new_code + ('\n' + suffix if suffix else '')
            return _write_and_verify(full_path, new_content, fix.new_code)

        # ── Tier 4: Anchor on most-unique line ──
        key_line = _most_unique_line(snippet_lines, content_lines)
        if key_line:
            for i, cl in enumerate(content_lines):
                if cl.strip() == key_line.strip():
                    logger.info(f"Tier 4 (anchor line) match at line {i}: {key_line[:60]}")
                    # Replace the block starting at the anchor line
                    block_len = len(snippet_lines)
                    prefix = '\n'.join(content_lines[:i])
                    suffix = '\n'.join(content_lines[i + block_len:])
                    new_content = (prefix + '\n' if prefix else '') + fix.new_snippet + ('\n' + suffix if suffix else '')
                    return _write_and_verify(full_path, new_content, fix.new_snippet)

        logger.error(f"Could not find original snippet in {fix.file_path}")
        logger.debug(f"Snippet was:\n{fix.original_snippet[:300]}")
        return False

    except Exception as e:
        logger.exception(f"Unexpected error while applying fix to {fix.file_path}: {e}")
        return False


def _replace_normalized(content: str, original: str, replacement: str) -> str | None:
    """
    Try to replace original (whitespace-normalized) inside content.
    Walks through line blocks and finds where the lines roughly match.
    """
    o_lines = [ln.strip() for ln in original.splitlines() if ln.strip()]
    c_lines = content.splitlines()

    for i in range(len(c_lines) - len(o_lines) + 1):
        block = [cl.strip() for cl in c_lines[i:i + len(o_lines)]]
        if block == o_lines:
            prefix = '\n'.join(c_lines[:i])
            suffix = '\n'.join(c_lines[i + len(o_lines):])
            return (prefix + '\n' if prefix else '') + replacement + ('\n' + suffix if suffix else '')
    return None


def _find_best_block(snippet_lines: list[str], content_lines: list[str]) -> tuple[int, int, float]:
    """Slide a window over content_lines and find the block with highest similarity."""
    win = max(1, len(snippet_lines))
    best_start, best_end, best_ratio = 0, win, 0.0
    for i in range(len(content_lines) - win + 1):
        block = content_lines[i:i + win]
        ratio = SequenceMatcher(None,
                                '\n'.join(snippet_lines),
                                '\n'.join(cl.strip() for cl in block)).ratio()
        if ratio > best_ratio:
            best_ratio, best_start, best_end = ratio, i, i + win
    return best_start, best_end, best_ratio


def _most_unique_line(snippet_lines: list[str], content_lines: list[str]) -> str:
    """Return the snippet line that appears exactly once in content (most distinctive)."""
    content_stripped = [cl.strip() for cl in content_lines]
    best = ""
    best_count = 999
    for sl in snippet_lines:
        stripped = sl.strip()
        if not stripped or len(stripped) < 10:
            continue
        count = content_stripped.count(stripped)
        if 0 < count < best_count:
            best_count = count
            best = stripped
    return best


def _write_and_verify(full_path: str, new_content: str, expected_snippet: str) -> bool:
    """Safely writes content to file and verifies the write."""
    backup_path = full_path + ".bak"
    shutil.copy2(full_path, backup_path)
    try:
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        with open(full_path, 'r', encoding='utf-8') as f:
            read_back = f.read()
            if expected_snippet in read_back:
                logger.info(f"Successfully patched {full_path}")
                return True
            else:
                logger.error(f"Verification failed for {full_path}: new snippet not found after write")
                shutil.move(backup_path, full_path)
                return False
    except Exception as e:
        logger.error(f"Failed to write or verify {full_path}: {e}")
        if os.path.exists(backup_path):
            shutil.move(backup_path, full_path)
        return False
    finally:
        if os.path.exists(backup_path):
            os.remove(backup_path)
