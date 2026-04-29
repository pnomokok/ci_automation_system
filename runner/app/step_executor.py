import logging
import os
from typing import Optional
from app.container_manager import ContainerManager
from app.log_collector import LogCollector
from app.timeout_guard import TimeoutGuard

logger = logging.getLogger(__name__)

class StepExecutor:
    def __init__(self, api_client, container_manager: ContainerManager):
        self.api_client = api_client
        self.container_manager = container_manager

    def execute_steps(self, pipeline_id: str, resolver, image: str, steps: list[str], step_ids: dict, workspace: str) -> Optional[bool]:
        """
        Executes the defined steps sequentially. 
        Returns True if SUCCESS, False if FAILED, None if STOPPED (e.g. timeout).
        """
        logger.info(f"Starting execution for pipeline {pipeline_id} with steps: {steps}")

        # Mount the named Docker volume so test containers can access workspace files.
        # Bind-mounting the subpath (/shared/workspaces/tmp-xxx) doesn't work with
        # named volumes via socket-based DinD — the host path doesn't exist outside
        # the runner container. We mount the whole volume and use working_dir instead.
        workspace_volume = os.getenv("WORKSPACE_VOLUME", "ci_automation_system_workspaces")
        volumes = {
            workspace_volume: {
                "bind": "/shared/workspaces",
                "mode": "rw"
            }
        }

        commands = resolver.get_commands()

        for step in steps:
            if step not in step_ids:
                error_msg = f"Step '{step}' is missing from step_ids dictionary."
                logger.error(error_msg)
                raise ValueError(error_msg)
                
            step_id = step_ids[step]

            if step not in commands:
                error_msg = f"Command for step '{step}' is missing from ci-config.yaml."
                logger.error(error_msg)
                raise ValueError(error_msg)

            command = ["sh", "-c", commands[step]]
            
            # Robust timeout parsing
            raw_timeout = resolver.get_timeout(step)
            try:
                # Handle possible malformed values by stripping whitespace 
                # (e.g. "5 5" -> ValueError)
                timeout_str = str(raw_timeout).strip()
                if ' ' in timeout_str:
                    raise ValueError(f"Malformed timeout string '{timeout_str}'")
                timeout = int(timeout_str)
            except ValueError:
                logger.warning(f"Invalid timeout value '{raw_timeout}' for step '{step}'. Using default 120.")
                timeout = 120

            logger.info(f"Executing step '{step}' (ID: {step_id}) with command: {command}")
            
            self.api_client.update_step_status(step_id, "RUNNING")
            
            # 1. create container
            container = self.container_manager.create_container(image, command, volumes, working_dir=workspace)
            if not container:
                logger.error(f"Failed to create container for step {step}")
                self.api_client.update_step_status(step_id, "FAILED")
                return False

            # 2. start container
            success = self.container_manager.start_container(container)
            if not success:
                logger.error(f"Failed to start container for step {step}")
                self.api_client.update_step_status(step_id, "FAILED")
                self.container_manager.cleanup_container(container)
                return False

            # 3. start log collection setup (we don't start the threaded stream for safety)
            log_collector = LogCollector(self.api_client, step_id)
            
            timeout_occurred = [False]
            
            def kill_action():
                logger.error(f"Timeout reached for step {step}. Killing container.")
                timeout_occurred[0] = True
                self.container_manager.stop_container(container)

            timeout_guard = TimeoutGuard(timeout, kill_action)
            timeout_guard.start()

            # 4. wait for container to finish
            try:
                result = container.wait()
                exit_code = result.get('StatusCode', -1)
            except Exception as e:
                logger.error(f"Error waiting for container to finish: {e}")
                exit_code = -1

            timeout_guard.stop()

            # 5. collect logs AFTER wait
            try:
                logs = container.logs(stdout=True, stderr=True)
                log_lines = logs.decode('utf-8', errors='replace').splitlines()
                if log_lines:
                    self.api_client.send_step_logs(step_id, log_lines)
            except Exception as e:
                logger.error(f"Failed to collect logs for step {step}: {e}")
            
            # 6. stop log collector (flushes if thread was active)
            log_collector.stop_collecting()
            
            # 7. cleanup container
            self.container_manager.cleanup_container(container)

            # Handle TIMEOUT separately
            if timeout_occurred[0]:
                logger.error(f"Step {step} marked as FAILED due to timeout.")
                self.api_client.update_step_status(step_id, "FAILED")
                return None # Pipeline STOPPED

            # Handle exit codes
            if exit_code != 0:
                logger.error(f"Step {step} failed with exit code {exit_code}")
                self.api_client.update_step_status(step_id, "FAILED", exit_code=exit_code)
                return False

            logger.info(f"Step {step} completed successfully.")
            self.api_client.update_step_status(step_id, "SUCCESS", exit_code=0)

        return True
