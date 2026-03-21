"""
File navigation tools for the LLM agent.

These tools let the agent explore and modify a cloned repository.
They are plain Python functions — no LLM calls here.
The LangGraph agent calls these tools iteratively to investigate the codebase.
"""

import os
import re
import logging
from typing import List, Optional


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

        dirs[:] = [
            d for d in dirs
            if d not in ("node_modules", ".git", "__pycache__", ".venv", "venv", ".tox", "dist", "build", "incidents", ".github")
        ]

        for filename in files:
            rel_path = os.path.relpath(os.path.join(root, filename), directory)
            results.append(rel_path)

    logger.info(f"list_files('{directory}'): found {len(results)} files")
    return results


def read_file(file_path: str) -> str:
    """
    Read the full contents of a file with line numbers.
    """
    if not os.path.isfile(file_path):
        return f"Error: '{file_path}' does not exist or is not a file."

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
            
        numbered = "".join(f"{i+1:4d}  {line}" for i, line in enumerate(lines))
        logger.info(f"read_file('{file_path}'): read {len(lines)} lines")
        return numbered
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
            if d not in ("node_modules", ".git", "__pycache__", ".venv", "venv", "dist", "build", "incidents", ".github")
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
    Read a specific range of lines from a file with line numbers prefixed.
    """
    if not os.path.isfile(file_path):
        return f"Error: '{file_path}' does not exist or is not a file."

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        start_idx = max(0, start_line - 1)
        end_idx = min(len(lines), end_line)
        selected = lines[start_idx:end_idx]

        result = "".join(f"{i+1:4d}  {line}" for i, line in enumerate(selected, start=start_idx + 1))

        logger.info(f"read_file_lines('{file_path}', {start_line}-{end_line}): {len(selected)} lines")
        return result
    except Exception as e:
        return f"Error reading '{file_path}': {e}"


def execute_command(command: str, cwd: str, container_id: Optional[str] = None) -> str:
    """
    Execute an arbitrary shell command in the repository.
    Can run either locally via subprocess or inside a Docker container.
    
    Args:
        command: The shell command to run.
        cwd: Current working directory (should be absolute).
        container_id: Optional Docker container ID to run the command in.
        
    Returns:
        Standard output and error from the command.
    """
    import subprocess
    from sandbox.docker_runner import docker_runner
    
    logger.info(f"execute_command('{command}') (container={container_id})")
    
    # Safeguard against LLM hallucinations (e.g., "Check the browser console")
    cmd_clean = command.strip()
    first_word = cmd_clean.split()[0].lower() if cmd_clean else ""
    forbidden_prefixes = ("check", "verify", "ensure", "i will", "now i", "wait", "first", "please")
    valid_prefixes = ("npm", "node", "python", "python3", "pytest", "pip", "pip3", "grep", "find", "ls", "cat", "curl", "wget", "ps", "sh", "bash", "git", "rm", "mv", "cp", "mkdir")
    
    is_valid = (
        first_word in valid_prefixes or 
        first_word.startswith(("./", "/"))
    ) and not any(cmd_clean.lower().startswith(p) for p in forbidden_prefixes)

    if not is_valid:
        logger.warning(f"Rejected invalid command hallucination: {command}")
        return f"Error: '{command}' is not a valid shell command. Use only supported tools (npm, pytest, python, etc.). Do not provide conversational instructions."

    if container_id:
        # Resolve workdir relative to container
        # Note: In our current setup, repo is mounted at /app
        output, exit_code = docker_runner.execute_command(container_id, command, workdir=cwd)
        return output

    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30  # 30s max — prevents telnet/curl hangs from blocking the agent
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
        logger.warning(f"Command timed out after 30s: {command}")
        return f"Error: Command timed out after 30s (likely a blocking network call): {command}"
    except Exception as e:
        return f"Error executing command: {e}"


def grep_ast(file_path: str, symbol_name: str) -> str:
    """
    AST-aware search for a symbol (function or class) in a Python file.
    Returns the source code of the symbol and its line range.
    
    This fulfills the 'AST-aware search' requirement by using the Python `ast` module.
    """
    import ast
    if not file_path.endswith(".py"):
        return f"Error: grep_ast currently only supports Python files. Use search_in_file for others."
    
    if not os.path.isfile(file_path):
        return f"Error: File '{file_path}' not found."
        
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
            
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
                if node.name == symbol_name:
                    start_line = node.lineno
                    # handle possible missing end_lineno in older versions, though 3.8+ should have it
                    end_line = getattr(node, "end_lineno", node.lineno + 1)
                    
                    # Extract the source for this node
                    lines = source.splitlines()
                    symbol_source = "\n".join(lines[start_line-1:end_line])
                    
                    return f"Found '{symbol_name}' at {os.path.basename(file_path)}:{start_line}-{end_line}:\n\n{symbol_source}"
                    
        return f"Symbol '{symbol_name}' not found in {os.path.basename(file_path)}."
    except Exception as e:
        return f"Error parsing {file_path}: {e}"


def write_scratchpad(content: str) -> str:
    """
    Writes to the agent's internal scratchpad to keep track of hypotheses and findings.
    This helps manage context by externalizing the agent's working memory.
    """
    return f"Scratchpad updated: {content}"


def summarize_file(file_path: str, content: str) -> str:
    """
    Generates a concise summary of a file's purpose and key functions.
    Used to keep the context window clean by replacing raw code with summaries.
    """
    from .fix_generator import call_llm
    prompt = f"Summarize the following code file ({file_path}) concisely, focusing on its main purpose and key functions:\n\n{content}"
    return call_llm(prompt)
