import functools
from naptha_sdk.agent_service import AgentService
from naptha_sdk.client.node import Node
from naptha_sdk.mas import MultiAgentService
from naptha_sdk.schemas import ModuleRun, ModuleRunInput
from naptha_sdk.utils import get_logger
import time

logger = get_logger(__name__)

class App:
    def __init__(self, naptha):
        self.naptha = naptha
        self.agent_services = []

    def agent_service(self, name, worker_node_url):
        def decorator(func):
            worker_node = Node(worker_node_url)
            self.agent_services.append(AgentService(name=name, fn=func, worker_node=worker_node, orchestrator_node=self.naptha.node))
            return func
        return decorator

    def publish_agent_packages(self):
        for agent_service in self.agent_services:
            agent_service.publish_package(self.naptha)

    async def register_agent_modules(self):
        for agent_service in self.agent_services:
            await agent_service.register_module(self.naptha)

    async def register_agent_services(self):
        for agent_service in self.agent_services:
            await agent_service.register_service(self.naptha)
        self.worker_node_urls = [agent_service.worker_node.node_url for agent_service in self.agent_services]
        self.worker_nodes = [Node(worker_node_url) for worker_node_url in self.worker_node_urls]
        logger.info(f"Worker Nodes: {self.worker_nodes}")

    def multi_agent_service(self, name):
        def decorator(func):
            self.multi_agent_service = MultiAgentService(self.naptha, name=name, fn=func)
            return func
        return decorator

    def publish_multi_agent_packages(self):
        self.multi_agent_service.publish_package()

    async def register_multi_agent_modules(self):
        await self.multi_agent_service.register_module()

    async def register_multi_agent_services(self):
        await self.multi_agent_service.register_service()
        self.orchestrator_node = self.naptha.node
        logger.info(f"Orchestrator node: {self.orchestrator_node.node_url}")

    async def run(self, run_params):
        consumer_id = self.naptha.user["id"]
        flow_run_input = {
            "name": self.multi_agent_service.name,
            "type": "template",
            "consumer_id": consumer_id,
            "orchestrator_node": self.naptha.node.node_url,
            "worker_nodes": self.worker_node_urls,
            "module_name": self.multi_agent_service.module_name,
            "module_params": run_params,
        }
        flow_run_input = ModuleRunInput(**flow_run_input)

        consumer = {
            "public_key": consumer_id.split(':')[1],
            'id': consumer_id,
        }

        logger.info(f"Starting MAS run: {flow_run_input}")
        logger.info(f"Checking user: {consumer}")
        consumer = await self.orchestrator_node.check_user(user_input=consumer)
        if consumer["is_registered"] == True:
            logger.info("Found user...", consumer)
        elif consumer["is_registered"] == False:
            logger.info("No user found. Registering user...")
            consumer = await self.orchestrator_node.register_user(user_input=consumer)
            logger.info(f"User registered: {consumer}.")

        logger.info(f"Running multi agent service on orchestrator node {self.orchestrator_node.node_url}: {flow_run_input}")
        flow_run = await self.orchestrator_node.run_task(module_run_input=flow_run_input)
        logger.info(f"Created multi agent service run on orchestrator node {self.orchestrator_node.node_url}: {flow_run}")

        current_results_len = 0
        while True:
            module_run = await self.orchestrator_node.check_task(flow_run)
            
            if isinstance(module_run, dict):
                module_run = ModuleRun(**module_run)

            output = f"{module_run.status} {module_run.module_type} {module_run.module_name}"
            if len(module_run.child_runs) > 0:
                output += f", task {len(module_run.child_runs)} {module_run.child_runs[-1].module_name} (node: {module_run.child_runs[-1].worker_nodes[0]})"
            print(output)

            if len(module_run.results) > current_results_len:
                print("Output: ", module_run.results[-1])
                current_results_len += 1

            logger.info(flow_run.status)  

            if module_run.status in ["completed", "error"]:
                break
            time.sleep(3)

        if module_run.status == 'completed':
            logger.info(module_run.results)
            self.agent_service_result = module_run.results
            return module_run.results
        else:
            logger.info(module_run.error_message)
            return module_run.error_message
