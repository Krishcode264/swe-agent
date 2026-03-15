"""
Local end-to-end test script for the swe-agent (P1 Module).

This script simulates the JSON payload that would normally be pushed
from Krishna's Node.js backend (via GitHub Webhooks -> Redis -> Python).
It feeds the payload directly into the agent_runner to verify that the
entire pipeline (Parsing -> Cloning -> Investigating -> Fixing -> Reporting) works.
"""

import json
import logging
from agent.agent_runner import process_incident

# Configure logging to see what the agent is thinking in the terminal
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%H:%M:%S"
)

# 1. Define a realistic incident task (exactly matching Krishna's queueService.ts output)
# We will point it at the real Rezinix-AI/shopstack-platform repository.
# We invent a plausible bug so Gemini has something to look for.
simulated_webhook_task = {
    "incidentId": "INC-TEST-001",
    "agent": "swe-agent",
    "repository": "Rezinix-AI/shopstack-platform",
    "issue_number": 999,
    "status": "queued",
    # These fields come from Krishna's updated Incident.ts model
    "title": "[TEST] Server crashes on startup due to missing database connection string",
    "description": "When starting the platform, the server immediately crashes before listening on the port.",
    "error_log": "TypeError: Cannot read properties of undefined (reading 'split')\n    at parseConnectionString (/src/config/db.js:12:34)\n    at connectDB (/src/server.js:45:12)"
}

from agent.agent_runner import process_incident, _generate_report_markdown
report = process_incident(simulated_webhook_task)

print("\n==================================================")
print("✅ Agent Workflow Complete")
print("==================================================")
print("\n--- Saving Resolution Report to docs/TEST_RUN_REPORT.md ---")

import os
os.makedirs("../docs", exist_ok=True)
report_path = os.path.join("..", "docs", "TEST_RUN_REPORT.md")
with open(report_path, "w", encoding="utf-8") as f:
    f.write(_generate_report_markdown(report))

print(f"Report saved. You can view it at: {report_path}")
