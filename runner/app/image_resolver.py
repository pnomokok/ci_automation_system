import os
import yaml
import logging

logger = logging.getLogger(__name__)

# Default mapping for runtimes
DEFAULT_IMAGES = {
    "python": "python:3.11",
    "nodejs": "node:18-slim",
    "java": "eclipse-temurin:17-jdk",
    "default": "ubuntu:22.04"
}

class ImageResolver:
    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
        self.config_file = os.path.join(workspace_path, "ci-config.yaml")
        self._config_cache = None

    def _load_config(self) -> dict:
        """Loads and validates the ci-config.yaml file."""
        if self._config_cache is not None:
            return self._config_cache

        if not os.path.exists(self.config_file):
            error_msg = f"Configuration file not found: {self.config_file}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        try:
            with open(self.config_file, "r") as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            error_msg = f"Invalid YAML in {self.config_file}: {e}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        if not isinstance(config, dict):
            error_msg = f"Configuration file {self.config_file} must be a valid YAML dictionary."
            logger.error(error_msg)
            raise ValueError(error_msg)

        self._config_cache = config
        return self._config_cache

    def resolve_image(self) -> str:
        """Reads config to determine the docker image."""
        config = self._load_config()
            
        # Check for explicitly defined image
        if "image" in config:
            logger.info(f"Using explicitly defined image: {config['image']}")
            return config["image"]

        # Fallback to runtime detection
        runtime = config.get("runtime", "default").lower()
        image = DEFAULT_IMAGES.get(runtime, DEFAULT_IMAGES["default"])
        logger.info(f"Resolved image {image} for runtime {runtime}")
        return image

    def get_commands(self) -> dict:
        """
        Reads ci-config.yaml and returns a dict mapping steps to commands.
        Example: {"install": "pip install -r requirements.txt"}
        """
        config = self._load_config()
        
        if "steps" not in config:
            error_msg = f"Missing required 'steps' section in {self.config_file}"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        steps_config = config["steps"]
        if not isinstance(steps_config, dict):
            error_msg = f"'steps' section in {self.config_file} must be a dictionary"
            logger.error(error_msg)
            raise ValueError(error_msg)

        commands = {}
        for step_name, step_details in steps_config.items():
            if not isinstance(step_details, dict):
                error_msg = f"Configuration for step '{step_name}' must be a dictionary"
                logger.error(error_msg)
                raise ValueError(error_msg)
                
            if "command" not in step_details:
                error_msg = f"Missing required 'command' for step '{step_name}' in {self.config_file}"
                logger.error(error_msg)
                raise ValueError(error_msg)
                
            commands[step_name] = step_details["command"]

        return commands

    def get_timeout(self, step_name: str) -> int:
        """
        Reads ci-config.yaml and returns the timeout for the given step.
        Returns 120 if not defined.
        """
        config = self._load_config()
        
        # We don't strictly validate 'steps' here to allow graceful fallback 
        # to the default if validation somehow passes in get_commands but not here
        # (though get_commands is usually called first)
        if "steps" not in config or not isinstance(config["steps"], dict):
            return 120
            
        step_config = config["steps"].get(step_name)
        if not isinstance(step_config, dict):
            return 120
            
        timeout = step_config.get("timeout", 120)
        
        try:
            return int(timeout)
        except ValueError:
            logger.warning(f"Invalid timeout value '{timeout}' for step '{step_name}'. Using default 120.")
            return 120
