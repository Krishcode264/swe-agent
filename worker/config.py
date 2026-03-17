import os
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
QUEUE_NAME = os.getenv("QUEUE_NAME", "incident_tasks")
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:5000/api")

# Placeholder for future AI integration (e.g. OpenAI or Gemini)
AI_API_KEY = os.getenv("AI_API_KEY", "")

# Gemini API key (primary LLM for agent reasoning)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# GitHub Personal Access Token (for PR creation)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

# Target repository to fix (shopstack-platform by default)
TARGET_REPO = os.getenv("TARGET_REPO", "Rezinix-AI/shopstack-platform")

