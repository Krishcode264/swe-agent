import logging
import os
from github import Github
from typing import Optional

logger = logging.getLogger(__name__)

class PRCreator:
    """Handles real GitHub Pull Request creation using PyGithub."""
    
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("GITHUB_TOKEN")
        if not self.token:
            logger.error("GITHUB_TOKEN not found in environment")
            self.github = None
        else:
            try:
                self.github = Github(self.token)
            except Exception as e:
                logger.error(f"Failed to initialize GitHub client: {e}")
                self.github = None

    def create_pull_request(
        self,
        repo_name: str,
        branch_name: str,
        title: str,
        body: str,
        base_branch: Optional[str] = None
    ) -> Optional[str]:
        """
        Creates a PR on GitHub.
        
        Args:
            repo_name: Full repository name (e.g., 'Krishcode264/swe-agent').
            branch_name: The head branch containing the fix.
            title: PR title.
            body: PR description (markdown).
            base_branch: The target branch (defaults to repo's default branch).
            
        Returns:
            The PR HTML URL if successful, None otherwise.
        """
        if not self.github:
            logger.error("GitHub client not available for PR creation")
            return None
            
        try:
            repo = self.github.get_repo(repo_name)
            
            # Use provided base_branch or repo's default branch
            target_base = base_branch or repo.default_branch
            logger.info(f"Targeting base branch: {target_base}")
            
            pr = repo.create_pull(
                title=title,
                body=body,
                head=branch_name,
                base=target_base
            )
            logger.info(f"PR created successfully: {pr.html_url}")
            return pr.html_url
        except Exception as e:
            error_msg = str(e)
            if hasattr(e, 'data'):
                error_msg += f" - {e.data}"
            logger.error(f"Failed to create PR in {repo_name}: {error_msg}")
            return None

# Helper instance
pr_creator = PRCreator()
