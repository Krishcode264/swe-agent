import os
import subprocess
import logging
from typing import Optional
from shared.models import TestResults

logger = logging.getLogger(__name__)

def run_tests(repo_path: str, service_type: Optional[str] = None, container_id: Optional[str] = None, workdir: Optional[str] = None) -> TestResults:
    """
    Detects the service type and runs the appropriate test suite.
    Attempts auto-recovery if missing dependencies are detected.
    """
    if not service_type:
        service_type = _detect_service_type(repo_path)
    
    # First attempt
    if service_type == "python":
        results = _run_pytest(repo_path, container_id=container_id, workdir=workdir)
    elif service_type == "node":
        results = _run_npm_test(repo_path, container_id=container_id, workdir=workdir)
    else:
        return TestResults(
            passed=False,
            output=f"Unknown or unsupported service type: {service_type}",
            tests_added=[]
        )

    # Check for missing dependencies and retry once if found
    if not results.passed:
        if _handle_missing_dependencies(results.output, repo_path, service_type, container_id=container_id, workdir=workdir):
            logger.info("Retrying tests after dependency installation...")
            if service_type == "python":
                results = _run_pytest(repo_path, container_id=container_id, workdir=workdir)
            elif service_type == "node":
                results = _run_npm_test(repo_path, container_id=container_id, workdir=workdir)
    
    return results

def install_dependencies(service_path: str, service_type: str, container_id: Optional[str] = None, workdir: Optional[str] = None) -> bool:
    """
    Installs dependencies for the given service type.
    
    Args:
        service_path: Absolute path to the service directory.
        service_type: 'python' or 'node'.
        container_id: Optional Docker container ID.
        workdir: Working directory inside the container.
        
    Returns:
        True if installation succeeded, False otherwise.
    """
    if service_type == "python":
        return _run_pip_install(service_path, container_id=container_id, workdir=workdir)
    elif service_type == "node":
        return _run_npm_install(service_path, container_id=container_id, workdir=workdir)
    return True

def _run_npm_install(service_path: str, container_id: Optional[str] = None, workdir: Optional[str] = None) -> bool:
    """Runs npm install in the service directory."""
    logger.info(f"Running npm install in {service_path} (container={container_id})")
    from .docker_runner import docker_runner
    try:
        # Check if package-lock.json exists
        has_lock = os.path.exists(os.path.join(service_path, "package-lock.json"))
        cmd = "npm ci" if has_lock else "npm install"
        
        if container_id:
            output, exit_code = docker_runner.execute_command(container_id, cmd, workdir=workdir or service_path)
            if exit_code != 0 and has_lock:
                 logger.info("Retrying with npm install...")
                 output, exit_code = docker_runner.execute_command(container_id, "npm install", workdir=workdir or service_path)
            return exit_code == 0

        cmd_list = ["npm", "ci"] if has_lock else ["npm", "install"]
        result = subprocess.run(
            cmd,
            cwd=service_path,
            capture_output=True,
            text=True,
            timeout=300
        )
        if result.returncode != 0:
            logger.error(f"npm install failed: {result.stderr}")
            # Fallback to plain npm install if npm ci failed
            if "npm ci" in str(cmd):
                logger.info("Retrying with npm install...")
                result = subprocess.run(["npm", "install"], cwd=service_path, capture_output=True, text=True, timeout=300)
        
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Error running npm install: {e}")
        return False

def _run_pip_install(service_path: str, container_id: Optional[str] = None, workdir: Optional[str] = None) -> bool:
    """Runs pip install in the service directory."""
    from .docker_runner import docker_runner
    logger.info(f"Running pip install in {service_path} (container={container_id})")
    try:
        if container_id:
            output, exit_code = docker_runner.execute_command(container_id, "pip install -r requirements.txt", workdir=workdir or service_path)
            return exit_code == 0
            
        result = subprocess.run(
            ["pip", "install", "-r", "requirements.txt"],
            cwd=service_path,
            capture_output=True,
            text=True,
            timeout=300
        )
        if result.returncode != 0:
            logger.error(f"pip install failed: {result.stderr}")
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Error running pip install: {e}")
        return False

def _detect_service_type(repo_path: str) -> str:
    """Detects service type based on file presence."""
    if os.path.exists(os.path.join(repo_path, "requirements.txt")) or \
       os.path.exists(os.path.join(repo_path, "pytest.ini")) or \
       any(f.endswith(".py") for f in os.listdir(repo_path) if os.path.isfile(os.path.join(repo_path, f))):
        return "python"
    
    if os.path.exists(os.path.join(repo_path, "package.json")):
        return "node"
    
    return "unknown"

def _run_pytest(repo_path: str, container_id: Optional[str] = None, workdir: Optional[str] = None) -> TestResults:
    """Runs pytest."""
    from .docker_runner import docker_runner
    logger.info(f"Running pytest in {repo_path} (container={container_id})")
    try:
        if container_id:
            output, exit_code = docker_runner.execute_command(container_id, "pytest -v", workdir=workdir or repo_path)
            return TestResults(passed=(exit_code == 0), output=output, tests_added=[])

        pytest_cmd = "pytest"
        result = subprocess.run(
            [pytest_cmd, "-v"],
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

def _run_npm_test(repo_path: str, container_id: Optional[str] = None, workdir: Optional[str] = None) -> TestResults:
    """Runs npm test."""
    from .docker_runner import docker_runner
    logger.info(f"Running npm test in {repo_path} (container={container_id})")
    try:
        if container_id:
            output, exit_code = docker_runner.execute_command(container_id, "npm test", workdir=workdir or repo_path)
            return TestResults(passed=(exit_code == 0), output=output, tests_added=[])

        cmd = ["npm", "test"]
        result = subprocess.run(
            cmd,
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

def _handle_missing_dependencies(test_output: str, service_path: str, service_type: str, container_id: Optional[str] = None, workdir: Optional[str] = None) -> bool:
    """
    Parses test output for missing dependency errors and attempts to install them.
    """
    import re
    from .docker_runner import docker_runner
    
    attempted = False
    
    # Pattern 1: Node.js "Please install X package manually"
    node_manual_match = re.search(r"Please install ([\w-]+) package manually", test_output)
    if node_manual_match and service_type == "node":
        package = node_manual_match.group(1)
        logger.info(f"Detected missing Node package: {package}. Attempting install...")
        if container_id:
            docker_runner.execute_command(container_id, f"npm install {package}", workdir=workdir or service_path)
        else:
            subprocess.run(["npm", "install", package], cwd=service_path, capture_output=True)
        attempted = True
        
    # Pattern 2: Node.js "Cannot find module 'X'"
    node_module_match = re.search(r"Cannot find module '([\w@/-]+)'", test_output)
    if node_module_match and service_type == "node":
        package = node_module_match.group(1)
        if not package.startswith("."):
            logger.info(f"Detected missing Node module: {package}. Attempting install...")
            if container_id:
                docker_runner.execute_command(container_id, f"npm install {package}", workdir=workdir or service_path)
            else:
                subprocess.run(["npm", "install", package], cwd=service_path, capture_output=True)
            attempted = True

    # Pattern 3: Python "ModuleNotFoundError: No module named 'X'"
    py_module_match = re.search(r"ModuleNotFoundError: No module named '([\w-]+)'", test_output)
    if py_module_match and service_type == "python":
        package = py_module_match.group(1)
        logger.info(f"Detected missing Python module: {package}. Attempting install...")
        if container_id:
            docker_runner.execute_command(container_id, f"pip install {package}", workdir=workdir or service_path)
        else:
            subprocess.run(["pip", "install", package], cwd=service_path, capture_output=True)
        attempted = True
        
    return attempted
