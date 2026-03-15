import requests
import logging
from config import BACKEND_API_URL

logger = logging.getLogger(__name__)

def update_incident_status(incident_id, status, message=None, extra_data=None):
    """
    Updates the incident status and timeline in the backend database.
    
    Args:
        incident_id: The unique incident identifier.
        status: The new status (e.g., 'running', 'tests_passed').
        message: Optional detail message for the timeline.
        extra_data: Optional dictionary of other fields to update in the Incident model.
    """
    try:
        url = f"{BACKEND_API_URL}/incidents/{incident_id}/status"
        payload = {
            "status": status,
            "message": message or f"Status transitioned to {status}",
            "extra_data": extra_data
        }
        
        response = requests.put(url, json=payload)
        response.raise_for_status()
        
        logger.info(f"Successfully updated incident {incident_id} to status: {status}")
        return True
    except Exception as e:
        logger.error(f"Failed to update incident status for {incident_id}: {e}")
        return False

def sync_incident_data(incident_id, data):
    """
    Syncs generic incident data back to the database.
    This can be used to update fields like description, repo_url, etc.
    """
    try:
        # For now, we can use the same status endpoint if we modify the backend 
        # to accept generic updates, or create a new dedicated PUT /incidents/:id endpoint.
        url = f"{BACKEND_API_URL}/incidents/{incident_id}"
        response = requests.put(url, json=data)
        response.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Failed to sync incident data for {incident_id}: {e}")
        return False
