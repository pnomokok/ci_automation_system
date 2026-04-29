import os
import sys
import json
import logging
import redis
from app.api_client import OrchestratorAPIClient
from app.image_resolver import ImageResolver
from app.container_manager import ContainerManager
from app.step_executor import StepExecutor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def main():
    logger.info("Starting CI Runner Service...")

    redis_host = os.environ.get("REDIS_HOST", "redis")
    redis_port = int(os.environ.get("REDIS_PORT", 6379))
    queue_name = os.environ.get("QUEUE_NAME", "pipeline_jobs")

    try:
        r = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
        r.ping()
        logger.info(f"Successfully connected to Redis at {redis_host}:{redis_port}")
    except redis.ConnectionError as e:
        logger.error(f"Failed to connect to Redis: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error connecting to redis: {e}")
        sys.exit(1)

    api_client = OrchestratorAPIClient()
    container_manager = ContainerManager()
    step_executor = StepExecutor(api_client, container_manager)

    logger.info(f"Listening for jobs on queue '{queue_name}'...")

    while True:
        pipeline_id = None
        try:
            # blpop blocks until an item is available
            result = r.blpop(queue_name, timeout=0)
            if not result:
                continue
            
            _, job_data_str = result
            job_data = json.loads(job_data_str)
            
            pipeline_id = job_data.get("pipeline_id")
            if not pipeline_id:
                logger.error("Job missing required field pipeline_id. Skipping.")
                continue

            logger.info(f"Job received for pipeline: {pipeline_id}")

            workspace = job_data.get("workspace")
            steps = job_data.get("steps", ["install", "build", "test"])
            step_ids = job_data.get("step_ids", {})

            if not workspace:
                logger.error(f"Pipeline {pipeline_id} missing required field workspace. Failing.")
                api_client.update_pipeline_status(pipeline_id, "FAILED")
                continue

            api_client.update_pipeline_status(pipeline_id, "RUNNING")

            # Resolve image based on workspace
            resolver = ImageResolver(workspace)
            image = resolver.resolve_image()

            # Execute steps
            exec_result = step_executor.execute_steps(
                pipeline_id=pipeline_id,
                resolver=resolver,
                image=image,
                steps=steps,
                step_ids=step_ids,
                workspace=workspace
            )

            if exec_result is True:
                status = "SUCCESS"
                logger.info(f"Job completed successfully for pipeline: {pipeline_id}")
            elif exec_result is False:
                status = "FAILED"
                logger.info(f"Job failed for pipeline: {pipeline_id}")
            else:
                status = "STOPPED"
                logger.info(f"Job stopped for pipeline: {pipeline_id}")

            api_client.update_pipeline_status(pipeline_id, status)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse job JSON: {e}")
            if pipeline_id:
                api_client.update_pipeline_status(pipeline_id, "FAILED")
        except Exception as e:
            logger.error(f"Unexpected error processing job: {e}")
            if pipeline_id:
                api_client.update_pipeline_status(pipeline_id, "FAILED")

if __name__ == "__main__":
    main()
