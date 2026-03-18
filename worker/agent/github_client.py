import logging

def create_pull_request(repo_url: str, branch_name: str, incident: dict) -> str:
    from agent.repo_manager import commit_changes, push_branch
    
    # Simulating standard git ops before opening a PR
    repo_path = f"/tmp/repos/{repo_url.split('/')[-1].replace('.git', '')}"
    
    commit_changes(repo_path, f"Fix: {incident.get('title')} (Incident {incident.get('incidentId')})")
    push_branch(repo_path, branch_name)
    
    logging.info(f"Simulating opening a PR on GitHub for branch {branch_name}")
    
    pr_url = f"{repo_url}/pull/101"
    logging.info(f"PR opened: {pr_url}")
    return pr_url
