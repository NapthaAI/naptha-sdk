import asyncio
from datetime import datetime
from naptha_sdk.schemas import AgentRun, AgentRunInput
from naptha_sdk.utils import get_logger
import pytz
import time
import traceback

logger = get_logger(__name__)
MAX_RETRIES = 5

async def run_task(task, flow_run, parameters) -> None:
    task_engine = TaskEngine(task, flow_run, parameters)
    await task_engine.init_run()
    try:
        await task_engine.start_run()
        while True:
            if task_engine.agent_run.status == "error":
                await task_engine.fail()
                break
            else:
                await task_engine.complete()
                break
            time.sleep(3)
        return task_engine.agent_result[-1]
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        await task_engine.fail()

class TaskEngine:
    def __init__(self, task, flow_run, parameters):
        self.task = task
        self.flow_run = flow_run
        self.parameters = parameters
        self.agent_result = None

        self.consumer = {
            "public_key": flow_run.consumer_id.split(':')[1],
            'id': flow_run.consumer_id,
        }

    async def init_run(self):
        if isinstance(self.flow_run, AgentRunInput):
            logger.info(f"Creating flow run on orchestrator node: {self.flow_run}")
            self.flow_run = await self.task.orchestrator_node.create_agent_run(agent_run_input=self.flow_run)
            logger.info(f"flow_run: {self.flow_run}")

        agent_run_input = {
            'consumer_id': self.consumer["id"],
            "worker_nodes": [self.task.worker_node.node_url],
            "agent_name": self.task.fn,
            "agent_run_type": "package",
            "agent_run_params": self.parameters,
            "parent_runs": [{k: v for k, v in self.flow_run.dict().items() if k not in ["child_runs", "parent_runs"]}],
        }
        self.agent_run_input = AgentRunInput(**agent_run_input)
        logger.info(f"Initializing agent run.")
        logger.info(f"Creating agent run for worker node on orchestrator node: {self.agent_run_input}")
        self.agent_run = await self.task.orchestrator_node.create_agent_run(agent_run_input=self.agent_run_input)
        logger.info(f"Created agent run for worker node on orchestrator node: {self.agent_run}")
        self.agent_run.start_processing_time = datetime.now(pytz.utc).isoformat()

        # Relate new agent run with parent flow run
        self.flow_run.child_runs.append(AgentRun(**{k: v for k, v in self.agent_run.dict().items() if k not in ["child_runs", "parent_runs"]}))
        logger.info(f"Adding agent run to parent flow run: {self.flow_run}")
        _ = await self.task.orchestrator_node.update_agent_run(agent_run=self.flow_run)

    async def start_run(self):
        logger.info(f"Starting agent run: {self.agent_run}")
        self.agent_run.status = "running"
        await self.task.orchestrator_node.update_agent_run(agent_run=self.agent_run)

        logger.info(f"Checking user: {self.consumer}")
        consumer = await self.task.worker_node.check_user(user_input=self.consumer)
        if consumer["is_registered"] == True:
            logger.info("Found user...", consumer)
        elif consumer["is_registered"] == False:
            logger.info("No user found. Registering user...")
            consumer = await self.task.worker_node.register_user(user_input=consumer)
            logger.info(f"User registered: {consumer}.")

        logger.info(f"Running agent on worker node {self.task.worker_node.node_url}: {self.agent_run_input}")
        agent_run = await self.task.worker_node.run_agent(agent_run_input=self.agent_run_input)
        logger.info(f"Created agent run on worker node {self.task.worker_node.node_url}: {agent_run}")

        retry_count = 0
        while retry_count < MAX_RETRIES:
            agent_run = await self.task.worker_node.check_agent_run(agent_run)
            if agent_run is None:
                logger.warning(f"check_agent_run returned None. Retrying... (Attempt {retry_count + 1}/{MAX_RETRIES})")
                retry_count += 1
                await asyncio.sleep(3)
                continue

            logger.info(f"Agent run status: {agent_run.status}")
            await self.task.orchestrator_node.update_agent_run(agent_run=agent_run)

            if agent_run.status in ["completed", "error"]:
                break
            await asyncio.sleep(3)

        if agent_run is None or retry_count == MAX_RETRIES:
            logger.error("Failed to retrieve agent status after multiple attempts")
            self.agent_run.status = "error"
            self.agent_run.error = True
            self.agent_run.error_message = "Failed to retrieve agent status"
            await self.task.orchestrator_node.update_agent_run(agent_run=self.agent_run)
            return None

        if agent_run.status == 'completed':
            logger.info(agent_run.results)
            self.agent_result = agent_run.results
            return agent_run.results
        else:
            logger.info(agent_run.error_message)
            return agent_run.error_message

    async def complete(self):
        self.agent_run.status = "completed"
        self.agent_run.results.extend(self.agent_result)
        self.flow_run.results.extend(self.agent_result)
        self.agent_run.error = False
        self.agent_run.error_message = ""
        self.agent_run.completed_time = datetime.now(pytz.timezone("UTC")).isoformat()
        self.agent_run.duration = (datetime.fromisoformat(self.agent_run.completed_time) - datetime.fromisoformat(self.agent_run.start_processing_time)).total_seconds()
        await self.task.orchestrator_node.update_agent_run(agent_run=self.agent_run)
        logger.info(f"Agent run completed: {self.agent_run}")

    async def fail(self):
        logger.error(f"Error running agent")
        error_details = traceback.format_exc()
        logger.error(f"Full traceback: {error_details}")
        self.agent_run.status = "error"
        self.agent_run.status = "error"
        self.agent_run.error = True
        self.agent_run.error_message = error_details
        self.agent_run.completed_time = datetime.now(pytz.timezone("UTC")).isoformat()
        self.agent_run.duration = (datetime.fromisoformat(self.agent_run.completed_time) - datetime.fromisoformat(self.agent_run.start_processing_time)).total_seconds()
        await self.task.orchestrator_node.update_agent_run(agent_run=self.agent_run)
