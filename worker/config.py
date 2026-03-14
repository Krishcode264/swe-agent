import os
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
QUEUE_NAME = os.getenv("QUEUE_NAME", "incident_tasks")
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:4000/api")

# Placeholder for future AI integration (e.g. OpenAI or Gemini)
AI_API_KEY = os.getenv("AI_API_KEY", "")
