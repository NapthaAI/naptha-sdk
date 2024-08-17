import asyncio
from datetime import datetime
import json
from naptha_sdk.schemas import ModuleRun, ModuleRunInput
from naptha_sdk.utils import get_logger
import pytz
import time
import traceback

logger = get_logger(__name__)

async def run_agent_service(agent_service, flow_run, parameters) -> None:
    agent_service_engine = AgentServiceEngine(agent_service, flow_run, parameters)
    await agent_service_engine.init_run()
    try:
        await agent_service_engine.start_run()
        while True:
            if agent_service_engine.agent_service_run.status == "error":
                await agent_service_engine.fail()
                break
            else:
                await agent_service_engine.complete()
                break
            time.sleep(3)
        return agent_service_engine.agent_service_result[-1]
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        await agent_service_engine.fail()

class AgentServiceEngine:
    def __init__(self, agent_service, flow_run, parameters):
        self.agent_service = agent_service
        self.flow_run = flow_run
        self.parameters = parameters
        self.agent_service_result = None

        self.consumer = {
            "public_key": flow_run.consumer_id.split(':')[1],
            'id': flow_run.consumer_id,
        }

    async def init_run(self):
        if isinstance(self.flow_run, ModuleRunInput):
            logger.info(f"Creating MAS run on orchestrator node: {self.flow_run}")
            self.flow_run = await self.agent_service.orchestrator_node.create_task_run(module_run_input=self.flow_run)
            logger.info(f"flow_run: {self.flow_run}")

        agent_service_run_input = {
            'consumer_id': self.consumer["id"],
            "worker_nodes": [self.agent_service.worker_node.node_url],
            "orchestrator_node": self.agent_service.orchestrator_node.node_url,
            "module_name": self.agent_service.fn,
            "module_type": "template",
            "module_params": self.parameters,
            "parent_runs": [{k: v for k, v in self.flow_run.dict().items() if k not in ["child_runs", "parent_runs"]}],
        }
        self.agent_service_run_input = ModuleRunInput(**agent_service_run_input)
        logger.info(f"Initializing agent service run.")
        logger.info(f"Creating agent service run for worker node on orchestrator node: {self.agent_service_run_input}")
        self.agent_service_run = await self.agent_service.orchestrator_node.create_task_run(module_run_input=self.agent_service_run_input)
        logger.info(f"Created agent service run for worker node on orchestrator node: {self.agent_service_run}")
        self.agent_service_run.start_processing_time = datetime.now(pytz.utc).isoformat()

        # Relate new agent service run with parent MAS run
        self.flow_run.child_runs.append(ModuleRun(**{k: v for k, v in self.agent_service_run.dict().items() if k not in ["child_runs", "parent_runs"]}))
        logger.info(f"Adding agent service run to parent MAS run: {self.flow_run}")
        _ = await self.agent_service.orchestrator_node.update_task_run(module_run=self.flow_run)

    async def start_run(self):
        logger.info(f"Starting agent service run: {self.agent_service_run}")
        self.agent_service_run.status = "running"
        await self.agent_service.orchestrator_node.update_task_run(module_run=self.agent_service_run)

        logger.info(f"Checking user: {self.consumer}")
        consumer = await self.agent_service.worker_node.check_user(user_input=self.consumer)
        if consumer["is_registered"] == True:
            logger.info("Found user...", consumer)
        elif consumer["is_registered"] == False:
            logger.info("No user found. Registering user...")
            consumer = await self.agent_service.worker_node.register_user(user_input=consumer)
            logger.info(f"User registered: {consumer}.")

        logger.info(f"Running agent service on worker node {self.agent_service.worker_node.node_url}: {self.agent_service_run_input}")
        agent_service_run = await self.agent_service.worker_node.run_task(module_run_input=self.agent_service_run_input)
        logger.info(f"Created agent service run on worker node {self.agent_service.worker_node.node_url}: {agent_service_run}")

        while True:
            agent_service_run = await self.agent_service.worker_node.check_task(agent_service_run)
            logger.info(agent_service_run.status)  
            await self.agent_service.orchestrator_node.update_task_run(module_run=agent_service_run)

            if agent_service_run.status in ["completed", "error"]:
                break
            time.sleep(3)

        if agent_service_run.status == 'completed':
            logger.info(agent_service_run.results)
            self.agent_service_result = agent_service_run.results
            return agent_service_run.results
        else:
            logger.info(agent_service_run.error_message)
            return agent_service_run.error_message

    async def complete(self):
        self.agent_service_run.status = "completed"
        self.agent_service_run.results.extend(self.agent_service_result)
        self.flow_run.results.extend(self.agent_service_result)
        self.agent_service_run.error = False
        self.agent_service_run.error_message = ""
        self.agent_service_run.completed_time = datetime.now(pytz.timezone("UTC")).isoformat()
        self.agent_service_run.duration = (datetime.fromisoformat(self.agent_service_run.completed_time) - datetime.fromisoformat(self.agent_service_run.start_processing_time)).total_seconds()
        await self.agent_service.orchestrator_node.update_task_run(module_run=self.agent_service_run)
        logger.info(f"Agent service run completed: {self.agent_service_run}")

    async def fail(self):
        logger.error(f"Error running agent service")
        error_details = traceback.format_exc()
        logger.error(f"Full traceback: {error_details}")
        self.agent_service_run.status = "error"
        self.agent_service_run.status = "error"
        self.agent_service_run.error = True
        self.agent_service_run.error_message = error_details
        self.agent_service_run.completed_time = datetime.now(pytz.timezone("UTC")).isoformat()
        self.agent_service_run.duration = (datetime.fromisoformat(self.agent_service_run.completed_time) - datetime.fromisoformat(self.agent_service_run.start_processing_time)).total_seconds()
        await self.agent_service.orchestrator_node.update_task_run(module_run=self.agent_service_run)
