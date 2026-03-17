import os
import re
import shutil
import logging
from ..shared.models import Fix

logger = logging.getLogger(__name__)

def apply_fix(repo_path: str, fix: Fix) -> bool:
    """
    Applies a code fix to a file within a repository using a tiered matching strategy.
    
    Args:
        repo_path: Absolute path to the repository root.
        fix: The Fix dataclass containing the file_path and code snippets.
        
    Returns:
        True if the fix was applied successfully, False otherwise.
    """
    full_path = os.path.join(repo_path, fix.file_path)
    
    if not os.path.exists(full_path):
        logger.error(f"File not found: {full_path}")
        return False

    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Tier 1: Exact Match
        if fix.original_snippet in content:
            new_content = content.replace(fix.original_snippet, fix.new_snippet, 1)
            return _write_and_verify(full_path, new_content, fix.new_snippet)

        # Tier 2: Whitespace-Agnostic Match
        # Replace any sequence of whitespace in the snippet with \s*
        # First, escape the snippet to handle regex special characters
        escaped_snippet = re.escape(fix.original_snippet)
        
        # Replace escaped whitespace characters (\ , \n, \t, etc.) with \s*
        # We also collapse multiple escaped spaces into a single \s*
        pattern_str = re.sub(r'(\\s|\\ |\\n|\\t|\\\r)+', r'\\s*', escaped_snippet)
        
        # We want to match the whole block, allowing flexible whitespace
        pattern = re.compile(pattern_str, re.MULTILINE | re.DOTALL)
        match = pattern.search(content)

        if match:
            logger.info(f"Tier 2 match found for {fix.file_path}")
            new_content = content[:match.start()] + fix.new_snippet + content[match.end():]
            return _write_and_verify(full_path, new_content, fix.new_snippet)

        logger.error(f"Could not find original snippet in {fix.file_path}")
        return False

    except Exception as e:
        logger.exception(f"Unexpected error while applying fix to {fix.file_path}: {e}")
        return False

def _write_and_verify(full_path: str, new_content: str, expected_snippet: str) -> bool:
    """Safely writes content to file and verifies the write."""
    # Create backup
    backup_path = full_path + ".bak"
    shutil.copy2(full_path, backup_path)
    
    try:
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        # Verify
        with open(full_path, 'r', encoding='utf-8') as f:
            read_back = f.read()
            if expected_snippet in read_back:
                return True
            else:
                logger.error(f"Verification failed for {full_path}: snippet not found after write")
                # Rollback
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
