import asyncio
from datetime import datetime
import json
from naptha_sdk.utils import get_logger
import pytz
import time
import traceback

logger = get_logger(__name__)

async def run_task(task, flow_run, parameters) -> None:
    task_engine = TaskEngine(task, flow_run, parameters)
    await task_engine.init_run()
    try:
        await task_engine.start_run()
        while True:
            if task_engine.task_run.status == "error":
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
    def __init__(self, task, flow_run, parameters):
        self.task = task
        self.flow_run = flow_run
        self.parameters = parameters
        self.task_result = None

        self.consumer = {
            "public_key": flow_run.consumer_id.split(':')[1],
            'id': flow_run.consumer_id,
        }

    async def init_run(self):
        self.task_run_input = {
            'consumer_id': self.consumer["id"],
            "module_name": self.task.fn,
            "module_params": self.parameters,
            "parent_runs": self.flow_run,
        }
        logger.info(f"Initializing task run: {self.task_run_input}")
        self.task_run = await self.task.orchestrator_node.create_task_run(task_run=self.task_run_input)
        self.task_run.start_processing_time = datetime.now(pytz.utc).isoformat()

    async def start_run(self):
        logger.info(f"Starting task run: {self.task_run}")
        self.task_run.status = "running"
        await self.task.orchestrator_node.update_task_run(task_run=self.task_run)

        logger.info(f"Checking user: {self.consumer}")
        consumer = await self.task.worker_node.check_user(user_input=self.consumer)
        if consumer["is_registered"] == True:
            logger.info("Found user...", consumer)
        elif consumer["is_registered"] == False:
            logger.info("No user found. Registering user...")
            consumer = await self.task.worker_node.register_user(user_input=consumer)
            logger.info(f"User registered: {consumer}.")

        logger.info(f"Running task: {self.task_run_input}")
        task_run = await self.task.worker_node.run_task(task_input=self.task_run_input, local=True)
        logger.info(f"Task run: {task_run}")

        # Relate new task run with parent flow run
        if self.flow_run.child_runs is None:
            self.flow_run.child_runs = task_run
        else:
            self.flow_run.child_runs.append(task_run)

        while True:
            task_run = await self.task.worker_node.check_task(task_run)
            logger.info(task_run.status)  
            await self.task.orchestrator_node.update_task_run(task_run=task_run)

            if status in ["completed", "error"]:
                break
            time.sleep(3)

        if task_run.status == 'completed':
            logger.info(task_run.results)
            self.task_result = task_run.results['output']
            return task_run.results['output']
        else:
            logger.info(task_run.error_message)
            return task_run.error_message

    async def complete(self):
        self.task_run.status = "completed"
        self.task_run.results = {"results": json.dumps(self.task_result)}
        self.task_run.error = False
        self.task_run.error_message = ""
        self.task_run.completed_time = datetime.now(pytz.timezone("UTC")).isoformat()
        self.task_run.duration = f"{(datetime.fromisoformat(self.task_run.completed_time) - datetime.fromisoformat(self.task_run.start_processing_time)).total_seconds()} seconds"
        await self.task.orchestrator_node.update_task_run(task_run=self.task_run)
        logger.info(f"Task run completed: {self.task_run}")

    async def fail(self):
        logger.error(f"Error running task")
        error_details = traceback.format_exc()
        logger.error(f"Full traceback: {error_details}")
        self.task_run.status = "error"
        self.task_run.status = "error"
        self.task_run.error = True
        self.task_run.error_message = error_details
        self.task_run.completed_time = datetime.now(pytz.timezone("UTC")).isoformat()
        self.task_run.duration = f"{(datetime.fromisoformat(self.task_run.completed_time) - datetime.fromisoformat(self.task_run.start_processing_time)).total_seconds()} seconds"
        await self.task.orchestrator_node.update_task_run(task_run=self.task_run)
