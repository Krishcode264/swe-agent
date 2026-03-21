import logging
import requests
import json
from typing import List, Dict, Optional, Any
from config import BACKEND_API_URL

logger = logging.getLogger(__name__)

class BaseMemory:
    """Base interface for different memory systems."""
    def store(self, key: str, value: Any):
        raise NotImplementedError

    def retrieve(self, query: str) -> Any:
        raise NotImplementedError

class EpisodicMemory(BaseMemory):
    """
    Handles long-term storage and retrieval of incident resolution traces.
    Connects to MongoDB via the Backend API.
    
    This lets the agent 'remember' how it fixed similar bugs in the past.
    """
    def __init__(self, repo_url: str):
        self.repo_url = repo_url

    def store(self, incident_id: str, trace: Dict[str, Any]):
        """Stores a resolution trace for future reference."""
        try:
            url = f"{BACKEND_API_URL}/memory/episodic"
            payload = {
                "incident_id": incident_id,
                "repo_url": self.repo_url,
                "trace": trace
            }
            response = requests.post(url, json=payload, timeout=5)
            if response.ok:
                logger.info(f"Episodic memory stored for {incident_id}")
            else:
                logger.warning(f"Backend rejected episodic memory: {response.text}")
        except Exception as e:
            logger.warning(f"Failed to store episodic memory: {e}")

    def retrieve(self, query: str) -> List[Dict[str, Any]]:
        """Searches for past incidents with similar error messages or root causes."""
        try:
            url = f"{BACKEND_API_URL}/memory/episodic/search"
            params = {"repo_url": self.repo_url, "q": query}
            response = requests.get(url, params=params, timeout=5)
            if response.ok:
                results = response.json().get("results", [])
                logger.info(f"Found {len(results)} similar episodic memories for query: {query[:30]}...")
                return results
        except Exception as e:
            logger.warning(f"Failed to search episodic memory: {e}")
        return []

class SemanticMemory(BaseMemory):
    """
    Placeholder for Vector Search integration.
    Will eventually connect to Qdrant/Pinecone for RAG across the codebase.
    """
    def store(self, key: str, value: Any):
        pass

    def retrieve(self, query: str) -> List[Dict[str, Any]]:
        # Mocking semantic search for now
        return []

class WorkingMemory:
    """
    Transient, in-run memory. 
    In LangGraph, this is essentially the 'AgentState'.
    """
    def __init__(self, state: Dict[str, Any]):
        self.state = state

    def get_summary(self) -> str:
        """Condensed summary of what has happened in the current run."""
        return f"Investigated {len(self.state.get('files_analyzed', []))} files. Current hypothesis: {self.state.get('hypothesis')}"
