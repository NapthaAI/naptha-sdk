from huggingface_hub import HfApi, login
import inspect
from naptha_sdk.code_extraction import create_poetry_package, extract_packages, add_dependency_to_pyproject, publish_hf_package, transform_code_as, transform_code_mas
from naptha_sdk.components.agent_service import AgentService
from naptha_sdk.client.hub import Hub
from naptha_sdk.schemas import ModuleRun, ModuleRunInput
from naptha_sdk.client.node import Node
from naptha_sdk.components.mas import MultiAgentService
from naptha_sdk.utils import AsyncMixin, get_logger
import time
from typing import Dict, List, Tuple

logger = get_logger(__name__)

class Naptha(AsyncMixin):
    """The entry point into Naptha."""

    def __init__(self,
            user,
            hub_username, 
            hub_password, 
            hf_username,
            hf_access_token,
            hub_url="ws://node.naptha.ai:3001/rpc",
            node_url="http://node.naptha.ai:7001",
            routing_url=None,
            indirect_node_id=None,
            *args, 
            **kwargs
    ):
        self.user = user
        self.hub_username = hub_username
        self.hub_password = hub_password
        self.hub_url = hub_url
        self.hf_username = hf_username
        login(hf_access_token)
        self.hf = HfApi()
        self.node_url = node_url
        self.routing_url = routing_url
        self.indirect_node_id = indirect_node_id
        self.node = Node(
            node_url=node_url,
            routing_url=routing_url,
            indirect_node_id=indirect_node_id
        )
        self.agent_services = []
        super().__init__()

    async def __ainit__(self,
            *args, 
            **kwargs):
        """Async constructor"""
        self.hub = await Hub(self.hub_username, self.hub_password, self.hub_url)

    def agent_service(self, name, worker_node_url):
        def decorator(func):
            worker_node = Node(worker_node_url)
            self.agent_services.append(AgentService(name=name, fn=func, worker_node=worker_node, orchestrator_node=self.node))
            return func
        return decorator

    def publish_agent_packages(self):
        for agent_service in self.agent_services:
            logger.info(f"Publishing Agent Package...")
            as_code = inspect.getsource(agent_service.fn)
            as_code = transform_code_as(as_code)
            packages = extract_packages(as_code)
            logger.info(f"PACKAGES: {packages}")
            create_poetry_package(agent_service.module_name)
            add_dependency_to_pyproject(agent_service.module_name, packages)
            publish_hf_package(self.hf, agent_service.module_name, agent_service.repo_id, as_code, self.hf_username)

    async def register_agent_modules(self):
        for agent_service in self.agent_services:
            module_config = {
                "name": agent_service.module_name,
                "description": agent_service.module_name,
                "author": f"user:{self.hf_username}",
                "url": f"https://huggingface.co/{self.hf_username}/{agent_service.repo_id}",
                "type": "template"
            }
            logger.info(f"Registering Agent Module {module_config}")
            module = await self.hub.create_module(module_config)

    async def register_agent_services(self):
        for agent_service in self.agent_services:
            agent_service_name = agent_service.name
            agent_service_config = {
                "name": agent_service_name,
                "description": agent_service_name,
                "module_name": agent_service.module_name,
                "worker_node_url": agent_service.worker_node.node_url,
            }
            logger.info(f"Registering Agent Service {agent_service_config}")
            service = await self.hub.create_service(agent_service_config)
        self.worker_node_urls = [agent_service.worker_node.node_url for agent_service in self.agent_services]
        self.worker_nodes = [Node(worker_node_url) for worker_node_url in self.worker_node_urls]
        logger.info(f"Worker Nodes: {self.worker_nodes}")

    def multi_agent_service(self, name):
        def decorator(func):
            self.multi_agent_service = MultiAgentService(self, name=name, fn=func)
            return func
        return decorator

    def publish_multi_agent_packages(self):
        logger.info(f"Publishing Multi-Agent Package...")
        mas_code = inspect.getsource(self.multi_agent_service.fn)
        mas_code = transform_code_mas(mas_code)
        packages = extract_packages(mas_code)
        logger.info(f"PACKAGES: {packages}")
        create_poetry_package(self.multi_agent_service.module_name)
        add_dependency_to_pyproject(self.multi_agent_service.module_name, packages)
        publish_hf_package(self.hf, self.multi_agent_service.module_name, self.multi_agent_service.repo_id, mas_code, self.hf_username)

    async def register_multi_agent_modules(self):
        module_config = {
            "name": self.multi_agent_service.module_name,
            "description": self.multi_agent_service.module_name,
            "author": f"user:{self.hf_username}",
            "url": f"https://huggingface.co/{self.hf_username}/{self.multi_agent_service.repo_id}",
            "type": "template"
        }
        logger.info(f"Registering Multi-Agent Module {module_config}")
        module = await self.hub.create_module(module_config)

    async def register_multi_agent_services(self):
        mas_name = self.multi_agent_service.name
        mas_config = {
            "name": mas_name,
            "description": mas_name,
            "module_name": self.multi_agent_service.module_name,
            "worker_node_url": self.node.node_url,
        }
        logger.info(f"Registering Multi-Agent Service {mas_config}")
        service = await self.hub.create_service(mas_config)
        self.orchestrator_node = self.node
        logger.info(f"Orchestrator node: {self.orchestrator_node.node_url}")

    async def deploy(self):
        self.publish_agent_packages()
        await self.register_agent_modules()
        await self.register_agent_services()

        self.publish_multi_agent_packages()
        await self.register_multi_agent_modules()
        await self.register_multi_agent_services()

    async def run(self, run_params):
        consumer_id = self.user["id"]
        flow_run_input = {
            "name": self.multi_agent_service.name,
            "type": "template",
            "consumer_id": consumer_id,
            "orchestrator_node": self.node.node_url,
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