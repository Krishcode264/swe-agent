import docker
import logging
import os
import time
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

class DockerRunner:
    """Manages Docker container lifecycle for sandboxed code execution."""
    
    def __init__(self):
        try:
            self.client = docker.from_env()
        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            self.client = None

    def create_sandbox(self, image_name: str, volume_mounts: dict) -> Optional[str]:
        """
        Starts a Docker container for sandboxed execution.
        
        Args:
            image_name: The Docker image to use.
            volume_mounts: Dictionary of local_path: {'bind': 'container_path', 'mode': 'rw'}.
            
        Returns:
            Container ID if successful, None otherwise.
        """
        if not self.client:
            return None
            
        try:
            container = self.client.containers.run(
                image=image_name,
                command="tail -f /dev/null", # Keep the container alive
                volumes=volume_mounts,
                detach=True,
                remove=True # Auto-cleanup when stopped
            )
            logger.info(f"Sandbox created: {container.id[:12]}")
            return container.id
        except Exception as e:
            logger.error(f"Failed to create sandbox: {e}")
            return None

    def execute_command(self, container_id: str, command: str, timeout: int = 120, workdir: Optional[str] = "/app") -> Tuple[str, int]:
        """
        Executes a command inside the sandbox container.
        
        Returns:
            Tuple of (output, exit_code).
        """
        if not self.client:
            return "Docker client not available", 1
            
        try:
            container = self.client.containers.get(container_id)
            # Only use workdir if explicitly provided or if default exists
            exec_result = container.exec_run(command, workdir=workdir)
            return exec_result.output.decode('utf-8'), exec_result.exit_code
        except Exception as e:
            logger.error(f"Failed to execute command in sandbox {container_id[:12]}: {e}")
            return str(e), 1

    def destroy_sandbox(self, container_id: str):
        """Stops and removes the sandbox container."""
        if not self.client:
            return
            
        try:
            container = self.client.containers.get(container_id)
            container.stop()
            logger.info(f"Sandbox destroyed: {container_id[:12]}")
        except Exception as e:
            logger.error(f"Failed to destroy sandbox {container_id[:12]}: {e}")

# Helper instance
docker_runner = DockerRunner()
