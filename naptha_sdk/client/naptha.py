import asyncio
from dotenv import load_dotenv
import inspect
from naptha_sdk.client.hub import Hub
from naptha_sdk.client.node import Node
from naptha_sdk.client.services import Services
from naptha_sdk.package_manager import AGENT_DIR, add_files_to_package, add_dependencies_to_pyproject, git_add_commit, init_agent_package, publish_ipfs_package, render_agent_code, write_code_to_package
from naptha_sdk.scrape import scrape_init, scrape_func
from naptha_sdk.user import get_public_key
from naptha_sdk.utils import get_logger
import os
from pathlib import Path
import time

logger = get_logger(__name__)

load_dotenv(override=True)

class Naptha:
    """The entry point into Naptha."""

    def __init__(self):
        self.public_key = get_public_key(os.getenv("PRIVATE_KEY")) if os.getenv("PRIVATE_KEY") else None
        self.hub_username = os.getenv("HUB_USER", None)
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

    async def __aenter__(self):
        """Async enter method for context manager"""
        await self.hub.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async exit method for context manager"""
        await self.hub.close()

    async def create_agent(self, name):
        async with self.hub:
            _, _, user_id = await self.hub.signin(self.hub_username, os.getenv("HUB_PASS"))
            agent_config = {
                "id": f"agent:{name}",
                "name": name,
                "description": name,
                "author": self.hub.user_id,
                "url": "None",
                "type": "package",
                "version": "0.1"
            }
            logger.info(f"Registering Agent {agent_config}")
            agent = await self.hub.create_or_update_agent(agent_config)
            if agent:
                logger.info(f"Agent {name} created successfully")
            else:
                logger.error(f"Failed to create agent {name}")

    async def publish_agents(self):
        logger.info(f"Publishing Agent Packages...")
        start_time = time.time()

        path = Path.cwd() / AGENT_DIR
        agents = [item.name for item in path.iterdir() if item.is_dir()]

        agent = agents[0]
        for agent in agents:
            git_add_commit(agent)
            _, response = await publish_ipfs_package(agent)
            logger.info(f"Published Agent: {agent}")
        
            # Register agent with hub
            async with self.hub:
                _, _, user_id = await self.hub.signin(self.hub_username, os.getenv("HUB_PASS"))
                agent_config = {
                    "id": f"agent:{agent}",
                    "name": agent,
                    "description": agent,
                    "author": self.hub.user_id,
                    "url": f'ipfs://{response["ipfs_hash"]}',
                    "type": "package",
                    "version": "0.1"
                }
                logger.info(f"Registering Agent {agent_config}")
                agent = await self.hub.create_or_update_agent(agent_config)

        end_time = time.time()
        total_time = end_time - start_time
        logger.info(f"Total time taken to publish {len(agents)} agents: {total_time:.2f} seconds")

    def build(self):
        asyncio.run(self.build_agents())

    async def connect_publish(self):
        await self.hub.connect()
        await self.hub.signin(os.getenv("HUB_USER"), os.getenv("HUB_PASS"))
        await self.publish_agents()
        await self.hub.close()

    def publish(self):
        asyncio.run(self.connect_publish())


def agent(name):
    def decorator(func):
        frame = inspect.currentframe()
        caller_frame = frame.f_back
        instantiation_file = caller_frame.f_code.co_filename
        variables = scrape_init(instantiation_file)
        agent_code, obj_name, local_modules, selective_import_modules, standard_import_modules, variable_modules = scrape_func(func, variables)
        agent_code = render_agent_code(name, agent_code, obj_name, local_modules, selective_import_modules, standard_import_modules, variable_modules)
        init_agent_package(name)
        write_code_to_package(name, agent_code)
        add_dependencies_to_pyproject(name, selective_import_modules + standard_import_modules)
        add_files_to_package(name, os.getenv("HUB_USER"))

        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(Naptha().create_agent(name))
        else:
            loop.run_until_complete(Naptha().create_agent(name))

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