import sys
import os
import time

# Add project root to path
PROJECT_ROOT = '/media/krishna/D/coding/swe-agent'
sys.path.append(PROJECT_ROOT)

from worker.sandbox.apply_fix import apply_fix
from worker.sandbox.docker_runner import docker_runner
from worker.shared.models import Fix

def run_e2e_test():
    app_dir = os.path.join(PROJECT_ROOT, 'dummy-app/docker-test')
    file_rel_path = 'dummy-app/docker-test/math.js'
    
    # 1. Prepare Fix Object
    fix = Fix(
        file_path=file_rel_path,
        explanation="Fixing addition bug in multiply function",
        original_snippet="return a + b;",
        new_snippet="return a * b;"
    )

    print("--- STEP 1: VERIFYING INITIAL FAILURE IN DOCKER ---")
    volume_mounts = {app_dir: {'bind': '/app', 'mode': 'rw'}}
    container_id = docker_runner.create_sandbox("node:20-alpine", volume_mounts)
    
    if not container_id:
        print("FAILED: Could not create sandbox")
        return

    try:
        # Run npm test (should fail)
        output, exit_code = docker_runner.execute_command(container_id, "npm test", workdir="/app")
        print(f"Initial Test Result - Exit Code: {exit_code}")
        print(f"Output: {output.strip()}")
        
        if exit_code == 0:
            print("ERROR: Test should have failed initially but passed!")
            return
        else:
            print("CONFIRMED: Test failed as expected.")

        print("\n--- STEP 2: APPLYING FIX LOCALLY ---")
        success = apply_fix(PROJECT_ROOT, fix)
        if not success:
            print("FAILED: Could not apply fix")
            return
        print("Fix applied successfully.")

        print("\n--- STEP 3: VERIFYING SUCCESS IN DOCKER ---")
        # Run npm test again (should pass)
        output, exit_code = docker_runner.execute_command(container_id, "npm test", workdir="/app")
        print(f"Final Test Result - Exit Code: {exit_code}")
        print(f"Output: {output.strip()}")
        
        if exit_code == 0 and "SUCCESS" in output:
            print("\n✅ END-TO-END VERIFICATION SUCCESSFUL!")
        else:
            print("\n❌ END-TO-END VERIFICATION FAILED!")

    finally:
        docker_runner.destroy_sandbox(container_id)

if __name__ == "__main__":
    run_e2e_test()
