"""
Repository manager — handles cloning and branching of the target repository.

Replaces the original stub that just created an empty folder.
Uses GitPython to perform real git operations.

Responsibilities:
  - Clone the target GitHub repository into a temporary directory
  - Create an agent-specific fix branch
  - Stage and commit the applied fix
  - Push the branch to remote
  - Cleanup temp directories after the workflow completes
"""

import os
import tempfile
import shutil
import logging

from git import Repo, GitCommandError
from config import GITHUB_TOKEN

logger = logging.getLogger(__name__)

# Base temp directory where all repos are cloned
CLONE_BASE_DIR = os.path.join(tempfile.gettempdir(), "swe_agent_repos")


def _build_auth_url(repo_url: str) -> str:
    """
    Inject GITHUB_TOKEN into the clone URL for private/authenticated repos.

    Transforms:
      https://github.com/org/repo.git
    Into:
      https://<token>@github.com/org/repo.git

    If no token is set, returns the original URL (still works for public repos).
    """
    if not GITHUB_TOKEN or "github.com" not in repo_url:
        return repo_url

    # Clean up trailing slash to avoid Git rejection
    clean_url = repo_url.rstrip("/")
    
    # If already has a token, return stripped version
    if "@" in clean_url and "github.com" in clean_url:
        return clean_url

    # Inject token
    if "https://" in clean_url:
        return clean_url.replace("https://", f"https://{GITHUB_TOKEN}@")
    
    return clean_url


def clone_repo(repo_url: str) -> str:
    """
    Clone a GitHub repository to a local temp directory.

    Args:
        repo_url: The HTTPS GitHub URL (e.g. "https://github.com/Rezinix-AI/shopstack-platform.git")
                  OR just the repo name (e.g. "Rezinix-AI/shopstack-platform")
                  which will be converted to a full URL automatically.

    Returns:
        Absolute path to the cloned repository on disk.

    Raises:
        GitCommandError: If cloning fails (bad URL, auth error, network, etc.)
    """
    # Normalize: if just "owner/repo" is passed, build the full URL
    if not repo_url.startswith("http"):
        repo_url = f"https://github.com/{repo_url}.git"

    # Derive a clean folder name: "Krishcode264/testing-repo-for-swe-agent" -> "testing-repo-for-swe-agent"
    repo_name = repo_url.rstrip("/").removesuffix(".git").split("/")[-1]
    clone_path = os.path.join(CLONE_BASE_DIR, repo_name)

    # If already cloned from a previous run, reset to a clean main state
    if os.path.isdir(clone_path):
        logger.info(f"Repo already exists at {clone_path}, resetting to clean main...")
        try:
            existing_repo = Repo(clone_path)
            
            # Determine the default branch (main or master)
            default_branch = "main"
            try:
                existing_repo.git.checkout("main")
            except GitCommandError:
                try:
                    existing_repo.git.checkout("master")
                    default_branch = "master"
                except GitCommandError:
                    pass  # Stay on whatever branch we're on
            
            # Hard reset to discard any agent-made changes from previous runs
            existing_repo.git.reset("--hard", f"origin/{default_branch}")
            
            # Remove untracked files/dirs (e.g. generated files, installed deps)
            existing_repo.git.clean("-fd")
            
            # Now pull latest from the remote default branch
            existing_repo.remotes.origin.pull(default_branch)
            
            logger.info(f"Reset {repo_name} to clean {default_branch} state successfully")
            return clone_path
        except Exception as e:
            logger.warning(f"Reset failed ({e}), deleting and re-cloning...")
            shutil.rmtree(clone_path, ignore_errors=True)

    # Fresh clone — depth=1 is a shallow clone (much faster, only latest commit)
    os.makedirs(CLONE_BASE_DIR, exist_ok=True)
    auth_url = _build_auth_url(repo_url)

    logger.info(f"Cloning {repo_name} into {clone_path}...")
    try:
        Repo.clone_from(auth_url, clone_path, depth=1)
        logger.info(f"Successfully cloned {repo_name}")
        return clone_path
    except GitCommandError as e:
        logger.error(f"Git clone failed for {repo_url}: {e}")
        raise


def create_branch(repo_path: str, branch_name: str) -> None:
    """
    Create and checkout a new branch in the cloned repo.

    Args:
        repo_path: Local path to the cloned repository.
        branch_name: Name of the branch to create (e.g. "fix/inc-0042")

    Raises:
        GitCommandError: If branch creation fails.
    """
    try:
        repo = Repo(repo_path)

        # If this branch already exists from a failed previous run, delete and recreate
        existing_branches = [b.name for b in repo.branches]
        if branch_name in existing_branches:
            logger.warning(f"Branch {branch_name} already exists — deleting and recreating...")
            # We must checkout a different branch before we can delete it
            default_branch = "main" if "main" in existing_branches else "master"
            # Fallback to whatever the active branch is if main/master don't exist
            if default_branch not in existing_branches and len(existing_branches) > 0:
                 default_branch = existing_branches[0]
            
            repo.git.checkout(default_branch)
            repo.git.branch("-D", branch_name)

        repo.git.checkout("-b", branch_name)
        logger.info(f"Created and checked out branch: {branch_name}")
    except GitCommandError as e:
        logger.error(f"Failed to create branch {branch_name}: {e}")
        raise


def commit_fix(repo_path: str, fix_file_path: str, incident_id: str) -> None:
    """
    Stage and commit only the fixed file (not the entire repo).

    Args:
        repo_path: Local path to the cloned repository.
        fix_file_path: Absolute path to the file that was modified by the agent.
        incident_id: Incident ID used in the commit message.
    """
    try:
        repo = Repo(repo_path)

        # Stage ONLY the specific modified file — never touch unrelated files
        relative_path = os.path.relpath(fix_file_path, repo_path)
        repo.index.add([relative_path])

        commit_message = (
            f"fix({incident_id}): apply agent-generated patch\n\n"
            f"Automated fix generated by swe-agent for incident {incident_id}.\n"
            f"Modified: {relative_path}"
        )
        repo.index.commit(commit_message)
        logger.info(f"Committed fix for {incident_id}: {relative_path}")
    except GitCommandError as e:
        logger.error(f"Failed to commit fix: {e}")
        raise


def push_branch(repo_path: str, branch_name: str) -> None:
    """
    Push the fix branch to the remote GitHub repository.

    Args:
        repo_path: Local path to the cloned repository.
        branch_name: Branch name to push.
    """
    try:
        repo = Repo(repo_path)
        origin = repo.remotes.origin

        # Re-inject auth token into remote URL before pushing
        # (GitPython strips credential helpers in some envs)
        auth_url = _build_auth_url(origin.url)
        origin.set_url(auth_url)

        origin.push(refspec=f"{branch_name}:{branch_name}")
        logger.info(f"Pushed branch {branch_name} to remote.")
    except GitCommandError as e:
        logger.error(f"Failed to push branch {branch_name}: {e}")
        raise


def has_uncommitted_changes(repo_path: str) -> bool:
    """
    Check if the repo has any uncommitted changes (modified, added, or untracked files).
    Used to detect side-effects like npm install modifying package.json.
    """
    try:
        repo = Repo(repo_path)
        # is_dirty includes staged + unstaged; untracked_files catches new files
        return repo.is_dirty(untracked_files=True)
    except Exception as e:
        logger.warning(f"Could not check git status for {repo_path}: {e}")
        return False


def commit_all_changes(repo_path: str, incident_id: str, message: str = "") -> bool:
    """
    Stage and commit ALL modified/untracked files in the repo.
    Used when a command (e.g. npm install) modified files without an explicit patch.

    Returns:
        True if any changes were committed, False if working tree was clean.
    """
    try:
        repo = Repo(repo_path)
        if not repo.is_dirty(untracked_files=True):
            logger.info(f"No changes to commit in {repo_path}")
            return False

        repo.git.add(A=True)  # Stage everything
        commit_msg = message or (
            f"fix({incident_id}): apply agent-generated changes\n\n"
            f"Automated fix generated by swe-agent for incident {incident_id}.\n"
            f"Changes include dependency or configuration updates."
        )
        repo.index.commit(commit_msg)
        logger.info(f"Committed all changes for {incident_id}")
        return True
    except GitCommandError as e:
        logger.error(f"Failed to commit all changes: {e}")
        raise


def cleanup_repo(repo_path: str) -> None:
    """
    Delete the cloned repository directory to free up disk space.
    Should be called after the full agent workflow completes (pass or fail).

    Args:
        repo_path: Local path to the cloned repository to delete.
    """
    try:
        if os.path.isdir(repo_path):
            shutil.rmtree(repo_path)
            logger.info(f"Cleaned up repo at {repo_path}")
    except Exception as e:
        logger.warning(f"Cleanup failed for {repo_path}: {e}")
