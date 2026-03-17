import sys
import os
import json
import logging

# Setup paths to import worker modules
sys.path.append('/media/krishna/D/coding/swe-agent/worker')

from agent.fix_generator import analyze_code
from agent.prompts import ANALYZE_CODE_PROMPT

# Configure logging to see what's happening
logging.basicConfig(level=logging.INFO)

def test_local_llm_reasoning():
    print("=== Local LLM Reasoning Test ===")
    
    # Sample data for the prompt
    incident_id = "INC-TEST-001"
    service = "node-service"
    error_message = "Expected 6, received 5"
    hypothesis = "The multiply function might be using addition instead of multiplication."
    file_path = "math.js"
    file_content = """
function multiply(a, b) {
  // Intentional bug: using + instead of *
  return a + b;
}

module.exports = { multiply };
"""

    print(f"Sending analysis request for {file_path} to local model...")
    
    try:
        # Call the actual analyze_code function which now uses Ollama
        result = analyze_code(
            incident_id=incident_id,
            service=service,
            error_message=error_message,
            hypothesis=hypothesis,
            file_path=file_path,
            file_content=file_content
        )
        
        print("\n--- Model Response (Parsed JSON) ---")
        print(json.dumps(result, indent=2))
        
        # Verify keys
        expected_keys = ["found_root_cause", "root_cause_explanation", "suggested_next_files"]
        missing_keys = [k for k in expected_keys if k not in result]
        
        if not missing_keys:
            print("\n✅ Verification SUCCESS: Model followed JSON format and provided all required keys.")
            if result.get("found_root_cause"):
                 print(f"✅ Root cause identified: {result['root_cause_explanation'][:100]}...")
        else:
            print(f"\n❌ Verification FAILED: Missing keys: {missing_keys}")
            
    except Exception as e:
        print(f"\n❌ Test crashed: {e}")

if __name__ == "__main__":
    test_local_llm_reasoning()
