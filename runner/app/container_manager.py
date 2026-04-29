import logging
import docker
from typing import Optional

logger = logging.getLogger(__name__)

class ContainerManager:
    def __init__(self):
        try:
            self.client = docker.from_env()
            logger.info("Successfully connected to Docker daemon.")
        except Exception as e:
            logger.error(f"Failed to connect to Docker daemon: {e}")
            raise

    def create_container(self, image: str, command: list, volumes: dict) -> Optional[docker.models.containers.Container]:
        """Creates a docker container with specified constraints."""
        if not volumes or not isinstance(volumes, dict):
            logger.error("Volumes parameter is empty or invalid.")
            return None

        try:
            logger.info(f"Creating container with image '{image}' and command '{command}'")
            # Ensure the image is available locally or pull it
            try:
                self.client.images.get(image)
            except docker.errors.ImageNotFound:
                logger.info(f"Image {image} not found locally, pulling...")
                self.client.images.pull(image)
                logger.info(f"Image pull completed for {image}")

            container = self.client.containers.create(
                image=image,
                command=command,
                volumes=volumes,
                network_mode="bridge",
                detach=True,
                tty=False,
                auto_remove=False,
                # Resource limits (example: 1 CPU, 512MB RAM)
                nano_cpus=1000000000,
                mem_limit="512m",
                working_dir="/workspace"
            )
            logger.info(f"Container created with ID {container.id[:12]}")
            return container
        except Exception as e:
            logger.error(f"Failed to create container: {e}")
            return None

    def start_container(self, container: docker.models.containers.Container) -> bool:
        """Starts a previously created container."""
        try:
            container.start()
            logger.info(f"Container {container.id[:12]} started successfully.")
            return True
        except Exception as e:
            logger.error(f"Container start failure for {container.id[:12]}: {e}")
            return False

    def stop_container(self, container: docker.models.containers.Container) -> bool:
        """Forcefully stops a running container."""
        try:
            container.reload()
            if container.status == "running":
                logger.info(f"Stopping container {container.id[:12]}...")
                # Kill instead of stop to immediately terminate
                container.kill()
                logger.info(f"Container {container.id[:12]} killed.")
            return True
        except docker.errors.NotFound:
             logger.warning(f"Container {container.id[:12]} already removed.")
             return True
        except Exception as e:
            logger.error(f"Failed to stop container {container.id[:12]}: {e}")
            return False

    def cleanup_container(self, container: docker.models.containers.Container):
        """Cleans up the container safely."""
        try:
            logger.info(f"Cleanup event: Removing container {container.id[:12]}...")
            container.remove(force=True)
            logger.info(f"Cleanup event: Container {container.id[:12]} removed.")
        except docker.errors.NotFound:
            # Expected behavior if already removed
            logger.info(f"Cleanup event: Container {container.id[:12]} not found (already removed).")
        except Exception as e:
            logger.error(f"Cleanup event: Error during container cleanup {container.id[:12]}: {e}")
