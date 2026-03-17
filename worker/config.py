import os
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
QUEUE_NAME = os.getenv("QUEUE_NAME", "incident_tasks")
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:4000/api")

# LLM Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")

# Gemini API keys (comma-separated list for rotation)
GEMINI_API_KEYS = [k.strip() for k in os.getenv("GEMINI_API_KEYS", "").split(",") if k.strip()]
# Fallback to single key if plural is not set
if not GEMINI_API_KEYS:
    primary_key = os.getenv("GEMINI_API_KEY", "")
    if primary_key:
        GEMINI_API_KEYS = [primary_key]

# GitHub Personal Access Token (for PR creation)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

# Target repository to fix (shopstack-platform by default)
TARGET_REPO = os.getenv("TARGET_REPO", "Rezinix-AI/shopstack-platform")

