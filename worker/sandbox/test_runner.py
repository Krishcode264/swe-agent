import os
import subprocess
import logging
import sys
from typing import Optional
from shared.models import TestResults

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
            output=f"No tests found: service type {service_type} could not be determined",
            tests_added=[],
            no_tests_found=True
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
        # Check for requirements.txt and install if present
        req_path = os.path.join(repo_path, "requirements.txt")
        if os.path.exists(req_path):
            logger.info(f"requirements.txt found in {repo_path}, installing dependencies...")
            
            # Special case for psycopg2-binary on Python 3.13
            # Version < 2.9.10 fails to compile on 3.13
            if sys.version_info >= (3, 13):
                try:
                    logger.info("Python 3.13 detected, ensuring compatible psycopg2-binary...")
                    subprocess.run(
                        [sys.executable, "-m", "pip", "install", "psycopg2-binary>=2.9.10"],
                        cwd=repo_path, capture_output=True, timeout=60
                    )
                except:
                    pass

            install_result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=300
            )
            if install_result.returncode != 0:
                logger.warning(f"pip install failed (may be minor): {install_result.stderr[:200]}")

        # Run pytest, capture output
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-v"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        passed = (result.returncode == 0)
        # Exit code 5 in pytest means no tests collected
        no_tests = (result.returncode == 5)
        output = result.stdout + "\n" + result.stderr
        
        return TestResults(passed=passed, output=output, tests_added=[], no_tests_found=no_tests)
        
    except subprocess.TimeoutExpired:
        return TestResults(passed=False, output="Test execution timed out after 120s", tests_added=[])
    except Exception as e:
        return TestResults(passed=False, output=f"Error running pytest: {str(e)}", tests_added=[])

def _run_npm_test(repo_path: str) -> TestResults:
    """Runs npm test via subprocess."""
    logger.info(f"Running npm test in {repo_path}")
    try:
        # Check if node_modules exists, if not run npm install
        if not os.path.exists(os.path.join(repo_path, "node_modules")):
            logger.info(f"node_modules missing in {repo_path}, running npm install...")
            install_result = subprocess.run(
                ["npm", "install"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=300
            )
            if install_result.returncode != 0:
                logger.warning(f"npm install failed: {install_result.stderr}")
                return TestResults(
                    passed=False, 
                    output=f"npm install failed:\n{install_result.stdout}\n{install_result.stderr}",
                    tests_added=[]
                )

        # Run npm test, capture output
        result = subprocess.run(
            ["npm", "test"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=180
        )
        
        passed = (result.returncode == 0)
        # Simple heuristic: if 'npm test' fails but mentions 'no tests' or similar
        no_tests = not passed and ("no tests" in result.stdout.lower() or "no tests" in result.stderr.lower())
        output = result.stdout + "\n" + result.stderr
        
        return TestResults(passed=passed, output=output, tests_added=[], no_tests_found=no_tests)
        
    except subprocess.TimeoutExpired:
        return TestResults(passed=False, output="Test execution timed out after 180s", tests_added=[])
    except Exception as e:
        return TestResults(passed=False, output=f"Error running npm test: {str(e)}", tests_added=[])
