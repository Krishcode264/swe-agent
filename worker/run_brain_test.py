"""
Specialized test script to demonstrate the Phase 1.5 Architecture "Brain" logic.
Focused on: Stack trace parsing, Multi-file investigation, and the Fix Handoff object.
"""
import sys
import os
import json
import logging

# Add the worker directory to path so we can import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from agent.agent_runner import process_incident
from shared.models import ResolutionReport

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s - %(message)s')

def run_brain_test():
    # Simulated incident with a realistic stack trace pointing to a specific file/line
    # Note: We use a path that exists in shopstack-platform
    fake_incident = {
        "incident_id": "INC-TEST-002",
        "repository": "Rezinix-AI/shopstack-platform",
        "issue_number": 888,
        "title": "ReferenceError in Database Configuration",
        "description": "The application crashes immediately on start. Looking at the logs, it seems like a variable is missing in the db setup.",
        "error_log": """
ReferenceError: db_url is not defined
    at connectDB (/node-service/src/config/db.js:15:20)
    at Object.<anonymous> (/node-service/src/app.js:22:1)
    at Module._compile (internal/modules/cjs/loader.js:959:30)
        """,
        "service": "node-service"
    }

    print("\n" + "="*50)
    print("🚀 STARTING BRAIN TEST: PHASE 1.5 ARCHITECTURE")
    print("="*50)
    print(f"Goal: Watch the agent parse the stack trace and go straight to src/config/db.js")
    
    try:
        report = process_incident(fake_incident)
        
        print("\n" + "="*50)
        print("✅ TEST COMPLETE - AGENT BRAIN OUTPUT")
        print("="*50)
        
        if report.fix:
            print(f"\n📂 File to Fix: {report.fix.file_path}")
            print(f"💡 Explanation: {report.fix.explanation}")
            print(f"❌ Original Snippet:\n{report.fix.original_snippet}")
            print(f"✅ Fixed Snippet:\n{report.fix.new_snippet}")
            print(f"🛠️ Is Environmental? {report.fix.no_fix_needed}")
        else:
            print("\n⚠️ No fix generated. Root cause:", report.root_cause)

        print(f"\n🧠 Files Analyzed in ReAct Loop: {report.files_analyzed}")
        print(f"📈 Confidence Score: {report.confidence_score}/100")
        print(f"🌍 Env Error Detected? {report.env_error_detected}")
        print("="*50)

    except Exception as e:
        print(f"❌ Test Script Failed: {e}")

if __name__ == "__main__":
    run_brain_test()
