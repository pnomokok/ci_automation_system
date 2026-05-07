import os
import sys
import json
import logging
import threading
import redis
from app.api_client import OrchestratorAPIClient
from app.container_manager import ContainerManager
from app.step_executor import StepExecutor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

MAX_WORKERS = int(os.environ.get("MAX_CONCURRENT_PIPELINES", 3))


def process_job(job_data: dict, api_client: OrchestratorAPIClient,
                step_executor: StepExecutor, redis_client) -> None:
    pipeline_id = job_data.get("pipeline_id")
    try:
        workspace = job_data.get("workspace")
        steps = job_data.get("steps", ["install", "build", "test"])
        step_ids = job_data.get("step_ids", {})

        if not workspace:
            logger.error(f"Pipeline {pipeline_id} missing required field workspace. Failing.")
            api_client.update_pipeline_status(pipeline_id, "FAILED")
            return

        api_client.update_pipeline_status(pipeline_id, "RUNNING")

        from app.image_resolver import ImageResolver
        resolver = ImageResolver(workspace)

        exec_result = step_executor.execute_steps(
            pipeline_id=pipeline_id,
            resolver=resolver,
            steps=steps,
            step_ids=step_ids,
            workspace=workspace,
            redis_client=redis_client,
        )

        if exec_result is True:
            final_status = "SUCCESS"
            logger.info(f"Job completed successfully for pipeline: {pipeline_id}")
        elif exec_result is False:
            final_status = "FAILED"
            logger.info(f"Job failed for pipeline: {pipeline_id}")
        else:
            final_status = "STOPPED"
            logger.info(f"Job stopped for pipeline: {pipeline_id}")

        api_client.update_pipeline_status(pipeline_id, final_status)

    except Exception as e:
        logger.error(f"Unexpected error processing pipeline {pipeline_id}: {e}")
        if pipeline_id:
            api_client.update_pipeline_status(pipeline_id, "FAILED")


def main():
    logger.info(f"Starting CI Runner Service (max_workers={MAX_WORKERS})...")

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

    # Semaphore: en fazla MAX_WORKERS pipeline aynı anda çalışır
    semaphore = threading.Semaphore(MAX_WORKERS)

    logger.info(f"Listening for jobs on queue '{queue_name}'...")

    while True:
        try:
            result = r.blpop(queue_name, timeout=0)
            if not result:
                continue

            _, job_data_str = result
            try:
                job_data = json.loads(job_data_str)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse job JSON: {e}")
                continue

            pipeline_id = job_data.get("pipeline_id")
            if not pipeline_id:
                logger.error("Job missing required field pipeline_id. Skipping.")
                continue

            logger.info(f"Job received for pipeline: {pipeline_id}")

            # Slot açılana kadar bekle (bloklamak yerine birer saniye polling)
            semaphore.acquire()

            def worker(jd=job_data):
                try:
                    process_job(jd, api_client, step_executor, r)
                finally:
                    semaphore.release()

            t = threading.Thread(target=worker, daemon=True)
            t.start()

        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")


if __name__ == "__main__":
    main()
