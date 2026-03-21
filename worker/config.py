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

# Rotating Gemini keys — comma-separated list. If set, the worker rotates on quota errors.
_raw_keys = os.getenv("GEMINI_API_KEYS", "")
GEMINI_API_KEYS: list[str] = [k.strip() for k in _raw_keys.split(",") if k.strip()] if _raw_keys else ([GEMINI_API_KEY] if GEMINI_API_KEY else [])

# GitHub Personal Access Token (for PR creation)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

# LLM Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini") # 'gemini' or 'ollama'
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")

# Target repository to fix (shopstack-platform by default)
TARGET_REPO = os.getenv("TARGET_REPO", "Rezinix-AI/shopstack-platform")

