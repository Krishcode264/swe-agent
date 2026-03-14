import logging
import time

def process_incident(incident):
    incident_id = incident.get("incidentId")
    repo_url = incident.get("repository")
    
    # Needs to import from queue_listener context, avoiding circular imports by inline proxy
    from queue_listener import update_incident_status
    
    from agent.repo_manager import clone_repo, create_branch
    from agent.fix_generator import generate_fix, apply_patch
    from agent.test_runner import run_tests
    from agent.github_client import create_pull_request
    
    try:
        logging.info(f"Starting agent workflow for {incident_id}")
        
        # 1. Clone Repo
        repo_path = clone_repo(repo_url)
        update_incident_status(incident_id, "running", "Repository cloned successfully")
        
        # 2. Generate Fix
        branch_name = f"fix/{incident_id.lower()}"
        create_branch(repo_path, branch_name)
        
        patch_spec = generate_fix(incident, repo_path)
        apply_patch(repo_path, patch_spec)
        update_incident_status(incident_id, "fix_generated", "Fix generated and applied to local repo")
        
        # 3. Run Tests
        tests_passed = run_tests(repo_path)
        if not tests_passed:
            update_incident_status(incident_id, "failed", "Tests failed after patch")
            return
            
        update_incident_status(incident_id, "tests_passed", "All tests passed successfully")
        
        # 4. Open PR
        pr_url = create_pull_request(repo_url, branch_name, incident)
        update_incident_status(incident_id, "pr_created", f"Pull request created: {pr_url}")
        
        logging.info(f"Finished agent workflow for {incident_id}")
    except Exception as e:
        logging.error(f"Error processing incident {incident_id}: {e}")
        update_incident_status(incident_id, "failed", f"Agent workflow failed: {e}")
