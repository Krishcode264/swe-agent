import os
import subprocess
import logging
from typing import Optional
from ..shared.models import TestResults

logger = logging.getLogger(__name__)

def run_tests(repo_path: str, service_type: Optional[str] = None) -> TestResults:
    """
    Detects the service type and runs the appropriate test suite.
    
    Args:
        repo_path: Absolute path to the repository root.
        service_type: Explicit service type ('python' or 'node'). If None, it's auto-detected.
        
    Returns:
        TestResults object containing pass/fail status and output.
    """
    if not service_type:
        service_type = _detect_service_type(repo_path)
    
    if service_type == "python":
        return _run_pytest(repo_path)
    elif service_type == "node":
        return _run_npm_test(repo_path)
    else:
        return TestResults(
            passed=False,
            output=f"Unknown or unsupported service type: {service_type}",
            tests_added=[]
        )

def _detect_service_type(repo_path: str) -> str:
    """Detects service type based on file presence."""
    if os.path.exists(os.path.join(repo_path, "requirements.txt")) or \
       os.path.exists(os.path.join(repo_path, "pytest.ini")) or \
       any(f.endswith(".py") for f in os.listdir(repo_path) if os.path.isfile(os.path.join(repo_path, f))):
        return "python"
    
    if os.path.exists(os.path.join(repo_path, "package.json")):
        return "node"
    
    return "unknown"

def _run_pytest(repo_path: str) -> TestResults:
    """Runs pytest via subprocess."""
    logger.info(f"Running pytest in {repo_path}")
    try:
        # Run pytest, capture output
        result = subprocess.run(
            ["pytest", "-v"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        passed = (result.returncode == 0)
        output = result.stdout + "\n" + result.stderr
        
        return TestResults(passed=passed, output=output, tests_added=[])
        
    except subprocess.TimeoutExpired:
        return TestResults(passed=False, output="Test execution timed out after 120s", tests_added=[])
    except Exception as e:
        return TestResults(passed=False, output=f"Error running pytest: {str(e)}", tests_added=[])

def _run_npm_test(repo_path: str) -> TestResults:
    """Runs npm test via subprocess."""
    logger.info(f"Running npm test in {repo_path}")
    try:
        # Run npm test, capture output
        result = subprocess.run(
            ["npm", "test"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=180
        )
        
        passed = (result.returncode == 0)
        output = result.stdout + "\n" + result.stderr
        
        return TestResults(passed=passed, output=output, tests_added=[])
        
    except subprocess.TimeoutExpired:
        return TestResults(passed=False, output="Test execution timed out after 180s", tests_added=[])
    except Exception as e:
        return TestResults(passed=False, output=f"Error running npm test: {str(e)}", tests_added=[])
