import sys
import os

# Ensure we can import modules from the project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from worker.sandbox.apply_fix import apply_fix
from worker.shared.models import Fix

def run_manual_test():
    repo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
    file_rel_path = 'worker/sandbox/tests/sample_script.js'
    
    print(f"--- PATCHING START ---")
    
    # Define the fix using the string-to-string format Shivam's agent produces
    fix = Fix(
        file_path=file_rel_path,
        explanation="Fixing discount calculation from addition to subtraction",
        original_snippet="return price + (price * (percentage / 100));",
        new_snippet="return price - (price * (percentage / 100));"
    )
    
    success = apply_fix(repo_path, fix)
    
    if success:
        print(f"SUCCESS: Patch applied to {file_rel_path}")
    else:
        print(f"FAILED: Could not apply patch.")

if __name__ == "__main__":
    run_manual_test()
