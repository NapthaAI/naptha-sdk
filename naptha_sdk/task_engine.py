import asyncio
from datetime import datetime
import json
from naptha_sdk.utils import get_logger
import pytz
import time
import traceback

logger = get_logger(__name__)

async def run_task(task, task_run, parameters) -> None:
    task_engine = TaskEngine(task, task_run, parameters)
    await task_engine.init_run()
    try:
        await task_engine.start_run()
        while True:
            if task_engine.task_run["status"] == "error":
                await task_engine.fail()
                break
            else:
                await task_engine.complete()
                break
            time.sleep(3)
        return task_engine.task_result
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        await task_engine.fail()

class TaskEngine:
    def __init__(self, task, task_run, parameters):
        self.task = task
        self.task_run = task_run
        self.parameters = parameters
        self.task_result = None

        self.consumer = {
            "public_key": task_run["consumer_id"].split(':')[1],
            'id': task_run["consumer_id"],
        }

    async def init_run(self):
        logger.info(f"Initializing task run: {self.task_run}")
        self.task_run["status"] = "processing"
        self.task_run["start_processing_time"] = datetime.now(pytz.utc).isoformat()
        self.task_run = {k: v for k, v in self.task_run.items() if v is not None}
        await self.task.orchestrator_node.create_task_run(task_run=self.task_run)

    async def start_run(self):
        logger.info(f"Starting task run: {self.task_run}")
        self.task_run["status"] = "running"
        await self.task.orchestrator_node.update_task_run(task_run=self.task_run)

        logger.info(f"Checking user: {self.consumer}")
        consumer = await self.task.worker_node.check_user(user_input=self.consumer)
        if consumer["is_registered"] == True:
            logger.info("Found user...", consumer)
        elif consumer["is_registered"] == False:
            logger.info("No user found. Registering user...")
            consumer = await self.task.worker_node.register_user(user_input=consumer)
            logger.info(f"User registered: {consumer}.")

        task_input = {
            'consumer_id': consumer["id"],
            "module_id": self.task.fn,
            "module_params": self.parameters,
        }

        logger.info(f"Running task: {task_input}")
        task_run = await self.task.worker_node.run_task(task_input=task_input, local=True)
        logger.info(f"Task run: {task_run}")

        while True:
            j = await self.task.worker_node.check_task({"id": task_run['id']})
            status = j['status']
            task_run["status"] = status
            logger.info(status)  
            await self.task.orchestrator_node.update_task_run(task_run=task_run)

            if status in ["completed", "error"]:
                break
            time.sleep(3)

        if j['status'] == 'completed':
            logger.info(j['reply'])
            self.task_result = j['reply']['output']
            return j['reply']['output']
        else:
            logger.info(j['error_message'])
            return j['error_message']

    async def complete(self):
        self.task_run["status"] = "completed"
        self.task_run["reply"] = {"results": json.dumps(self.task_result)}
        self.task_run["error"] = False
        self.task_run["error_message"] = ""
        self.task_run["completed_time"] = datetime.now(pytz.timezone("UTC")).isoformat()
        self.task_run["duration"] = f"{(datetime.fromisoformat(self.task_run['completed_time']) - datetime.fromisoformat(self.task_run['start_processing_time'])).total_seconds()} seconds"
        await self.task.orchestrator_node.update_task_run(task_run=self.task_run)
        logger.info(f"Task run completed: {self.task_run}")

    async def fail(self):
        logger.error(f"Error running task")
        error_details = traceback.format_exc()
        logger.error(f"Full traceback: {error_details}")
        self.task_run["status"] = "error"
        self.task_run["status"] = "error"
        self.task_run["error"] = True
        self.task_run["error_message"] = error_details
        self.task_run["completed_time"] = datetime.now(pytz.timezone("UTC")).isoformat()
        self.task_run["duration"] = f"{(datetime.fromisoformat(self.task_run['completed_time']) - datetime.fromisoformat(self.task_run['start_processing_time'])).total_seconds()} seconds"
        await self.task.orchestrator_node.update_task_run(task_run=self.task_run)
