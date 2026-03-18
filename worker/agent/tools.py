"""
File navigation tools for the LLM agent.

These tools let the agent explore and modify a cloned repository.
They are plain Python functions — no LLM calls here.
The LangGraph agent calls these tools iteratively to investigate the codebase.
"""

import os
import re
import logging
from typing import List


logger = logging.getLogger(__name__)


def list_files(directory: str, max_depth: int = 3) -> List[str]:
    """
    List all files in a directory recursively up to max_depth.

    Args:
        directory: Absolute path to the directory to list.
        max_depth: Maximum directory depth to traverse (default 3).

    Returns:
        List of file paths relative to the given directory.
    """
    if not os.path.isdir(directory):
        return [f"Error: '{directory}' is not a valid directory."]

    results = []
    base_depth = directory.rstrip(os.sep).count(os.sep)

    for root, dirs, files in os.walk(directory):
        current_depth = root.rstrip(os.sep).count(os.sep) - base_depth
        if current_depth >= max_depth:
            dirs.clear()  # Don't descend further
            continue

        # Skip common non-essential directories
        dirs[:] = [
            d for d in dirs
            if d not in ("node_modules", ".git", "__pycache__", ".venv", "venv", ".tox", "dist", "build")
        ]

        for filename in files:
            rel_path = os.path.relpath(os.path.join(root, filename), directory)
            results.append(rel_path)

    logger.info(f"list_files('{directory}'): found {len(results)} files")
    return results


def read_file(file_path: str) -> str:
    """
    Read the full contents of a file.

    Args:
        file_path: Absolute path to the file.

    Returns:
        File contents as a string, or an error message if the file cannot be read.
    """
    if not os.path.isfile(file_path):
        return f"Error: '{file_path}' does not exist or is not a file."

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        logger.info(f"read_file('{file_path}'): {len(content)} chars")
        return content
    except Exception as e:
        return f"Error reading '{file_path}': {e}"


def search_in_file(file_path: str, pattern: str) -> List[str]:
    """
    Search for a string pattern in a file. Returns matching lines with line numbers.

    Args:
        file_path: Absolute path to the file to search.
        pattern: Text pattern to search for (case-insensitive).

    Returns:
        List of strings in the format "line_number: line_content" for each match.
    """
    if not os.path.isfile(file_path):
        return [f"Error: '{file_path}' does not exist or is not a file."]

    try:
        matches = []
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f, start=1):
                if re.search(pattern, line, re.IGNORECASE):
                    matches.append(f"{i}: {line.rstrip()}")

        logger.info(f"search_in_file('{file_path}', '{pattern}'): {len(matches)} matches")
        return matches if matches else [f"No matches found for '{pattern}' in '{file_path}'."]
    except Exception as e:
        return [f"Error searching '{file_path}': {e}"]


def search_in_directory(directory: str, pattern: str, extensions: List[str] = None) -> List[str]:
    """
    Search for a string pattern across all files in a directory.
    Useful for finding function definitions, variable usage, error strings, etc.

    Args:
        directory: Absolute path to search within.
        pattern: Text pattern to search for (case-insensitive).
        extensions: Optional list of file extensions to include (e.g., ['.py', '.js']).

    Returns:
        List of strings in the format "file_path:line_number: line_content" for each match.
    """
    if not os.path.isdir(directory):
        return [f"Error: '{directory}' is not a valid directory."]

    matches = []
    for root, dirs, files in os.walk(directory):
        # Skip non-essential directories
        dirs[:] = [
            d for d in dirs
            if d not in ("node_modules", ".git", "__pycache__", ".venv", "venv", "dist", "build")
        ]

        for filename in files:
            if extensions and not any(filename.endswith(ext) for ext in extensions):
                continue

            file_path = os.path.join(root, filename)
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    for i, line in enumerate(f, start=1):
                        if re.search(pattern, line, re.IGNORECASE):
                            rel_path = os.path.relpath(file_path, directory)
                            matches.append(f"{rel_path}:{i}: {line.rstrip()}")
            except Exception:
                continue  # Skip binary files or permission errors

    logger.info(f"search_in_directory('{directory}', '{pattern}'): {len(matches)} matches")
    return matches[:50]  # Cap results to avoid flooding context


def write_file(file_path: str, content: str) -> str:
    """
    Write content to a file. Creates parent directories if needed.

    Args:
        file_path: Absolute path to the file.
        content: The full content to write.

    Returns:
        Success or error message.
    """
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"write_file('{file_path}'): wrote {len(content)} chars")
        return f"Successfully wrote {len(content)} characters to '{file_path}'."
    except Exception as e:
        return f"Error writing to '{file_path}': {e}"


def read_file_lines(file_path: str, start_line: int, end_line: int) -> str:
    """
    Read a specific range of lines from a file.
    Useful for reading large files without loading everything into context.

    Args:
        file_path: Absolute path to the file.
        start_line: First line to read (1-indexed, inclusive).
        end_line: Last line to read (1-indexed, inclusive).

    Returns:
        The requested lines with line numbers prefixed.
    """
    if not os.path.isfile(file_path):
        return f"Error: '{file_path}' does not exist or is not a file."

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        start_idx = max(0, start_line - 1)
        end_idx = min(len(lines), end_line)
        selected = lines[start_idx:end_idx]

        result = ""
        for i, line in enumerate(selected, start=start_idx + 1):
            result += f"{i}: {line}"

        logger.info(f"read_file_lines('{file_path}', {start_line}-{end_line}): {len(selected)} lines")
        return result
    except Exception as e:
        return f"Error reading '{file_path}': {e}"


def execute_command(command: str, cwd: str) -> str:
    """
    Execute an arbitrary shell command in the repository.
    
    Args:
        command: The shell command to run.
        cwd: Current working directory (should be absolute).
        
    Returns:
        Standard output and error from the command.
    """
    import subprocess
    logger.info(f"execute_command('{command}') in {cwd}")
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=120
        )
        output = result.stdout
        if result.stderr:
            output += "\n--- ERRORS ---\n" + result.stderr
        
        # Cap output size to avoid blowing up context
        if len(output) > 5000:
            output = output[:2500] + "\n... [TRUNCATED] ...\n" + output[-2500:]
            
        logger.info(f"execute_command result: code {result.returncode}, {len(output)} chars")
        return output
    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after 120s: {command}"
    except Exception as e:
        return f"Error executing command: {e}"
