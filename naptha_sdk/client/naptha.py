import asyncio
from dotenv import load_dotenv
import inspect
from naptha_sdk.client.hub import Hub
from naptha_sdk.client.node import Node
from naptha_sdk.client.services import Services
from naptha_sdk.package_manager import add_files_to_package, add_dependencies_to_pyproject, git_add_commit, init_agent_package, publish_ipfs_package, render_agent_code
from naptha_sdk.scrape import scrape_init, scrape_func
from naptha_sdk.user import get_public_key
from naptha_sdk.utils import get_logger
import os
import time
from typing import Dict, List, Tuple

logger = get_logger(__name__)

load_dotenv(override=True)

class Naptha:
    """The entry point into Naptha."""

    def __init__(self):
        self.public_key = get_public_key(os.getenv("PRIVATE_KEY")) if os.getenv("PRIVATE_KEY") else None
        self.hub_username = os.getenv("HUB_USERNAME", None)
        self.hub_url = os.getenv("HUB_URL", None)
        self.node_url = os.getenv("NODE_URL", None)
        self.routing_url = os.getenv("ROUTING_URL", None)
        self.indirect_node_id = os.getenv("INDIRECT_NODE_ID", None)
        self.node = Node(
            node_url=self.node_url,
            routing_url=self.routing_url,
            indirect_node_id=self.indirect_node_id
        )
        self.services = Services()
        self.hub = Hub(self.hub_url, self.public_key)  
        self.agents = []

    async def __aenter__(self):
        """Async enter method for context manager"""
        await self.hub.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async exit method for context manager"""
        await self.hub.close()

    async def build_agents(self):
        logger.info(f"Building Agent Packages...")
        start_time = time.time()
        for agent in self.agents:
            init_agent_package(agent.name)
            agent_code, local_modules, selective_import_modules, standard_import_modules, variable_modules = scrape_func(agent.fn, self.variables)
            agent_code = render_agent_code(agent.name, agent_code, local_modules, selective_import_modules, standard_import_modules, variable_modules)
            add_dependencies_to_pyproject(agent.name, selective_import_modules + standard_import_modules)
            add_files_to_package(agent.name, agent_code, self.hub_username)
        end_time = time.time()
        total_time = end_time - start_time
        logger.info(f"Total time taken to build {len(self.agents)} agents: {total_time:.2f} seconds")

    async def publish_agents(self):
        logger.info(f"Publishing Agent Packages...")
        start_time = time.time()
        for agent in self.agents:
            git_add_commit(agent.name)
            success, response = await publish_ipfs_package(agent.name)

            agent_config = {
                "id": f"agent:{agent.name}",
                "name": agent.name,
                "description": agent.name,
                "author": self.hub.user_id,
                "url": f"ipfs://{response['ipfs_hash']}",
                "type": "package",
                "version": "0.1"
            }
            logger.info(f"Registering Agent {agent_config}")
            agent = await self.hub.create_or_update_agent(agent_config)
            logger.info(f"Published Agent: {agent}")
        
        end_time = time.time()
        total_time = end_time - start_time
        logger.info(f"Total time taken to publish {len(self.agents)} agents: {total_time:.2f} seconds")

    def build(self):
        asyncio.run(self.build_agents())

    async def connect_publish(self):
        await self.hub.connect()
        await self.hub.signin(os.getenv("HUB_USER"), os.getenv("HUB_PASS"))
        await self.publish_agents()
        await self.hub.close()

    def publish(self):
        asyncio.run(self.connect_publish())


def agent(name, worker_node_url):
    def decorator(func):
        frame = inspect.currentframe()
        caller_frame = frame.f_back
        instantiation_file = caller_frame.f_code.co_filename
        variables = scrape_init(instantiation_file)
        agent_code, local_modules, selective_import_modules, standard_import_modules, variable_modules = scrape_func(func, variables)
        agent_code = render_agent_code(name, agent_code, local_modules, selective_import_modules, standard_import_modules, variable_modules)
 
        dependencies = selective_import_modules + standard_import_modules
        print("DEPENDENCIES", dependencies)
        print("AGENT CODE", agent_code)

        # self.agents.append(Agent(name=name, fn=func, worker_node_url=worker_node_url))
        return func
    return decorator

class Agent:
    def __init__(self, 
        name, 
        fn, 
        worker_node_url, 
    ):
        self.name = name
        self.fn = fn
        self.worker_node_url = worker_node_url
        self.repo_id = name