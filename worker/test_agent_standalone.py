import logging
import json
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Import the agent runner
# We need to make sure we are in the worker directory for imports to work
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agent.agent_runner import process_incident

def test_standalone_agent():
    """
    Test the agent workflow on a real (but small) incident.
    This will use the TARGET_REPO from .env or a default one.
    """
    # Create a dummy incident that matches the math bug
    dummy_incident = {
        "incidentId": "TEST-STANDALONE-002",
        "title": "Logic Error in math.js (Multiplication performing Addition)",
        "description": "The math.js file has a logic bug where the multiply function is adding numbers instead of multiplying them. Please correct the operator in math.js.",
        "repository": "Krishcode264/testing-repo-for-swe-agent",
        "service": "node-service",
        "error_log": "Logic Error: multiply(2, 3) returned 5. The implementation in math.js is likely using '+' instead of '*'."
    }

    logging.info("Starting standalone agent test...")
    try:
        report = process_incident(dummy_incident)
        
        logging.info("=== Test Report Results ===")
        logging.info(f"Incident ID: {report.incident_id}")
        logging.info(f"Status: {'Passed' if report.test_results and report.test_results.passed else 'Failed'}")
        logging.info(f"Confidence: {report.confidence_score}")
        if report.pr_url:
            logging.info(f"PR Created: {report.pr_url}")
        else:
            logging.info("No PR was created.")
            
        print("\n--- REPORT MARKDOWN ---")
        print(report.report_markdown)
        print("-----------------------\n")
        
        if report.test_results and report.test_results.passed and report.pr_url:
            logging.info("SUCCESS: The agent successfully fixed the bug and created a PR!")
        else:
            logging.warning("PARTIAL SUCCESS: The agent finished but might not have fixed the bug or created a PR.")

    except Exception as e:
        logging.error(f"Standalone test failed with error: {e}")
        import traceback
        logging.error(traceback.format_exc())

if __name__ == "__main__":
    test_standalone_agent()
