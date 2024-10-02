from naptha_sdk.client.hub import Hub
from naptha_sdk.client.node import Node
from naptha_sdk.client.services import Services
from naptha_sdk.package_manager import add_files_to_package, add_dependency_to_pyproject, create_poetry_package, publish_ipfs_package, transform_code_agent
from naptha_sdk.scrape import scrape_code
from naptha_sdk.utils import get_logger
from typing import Dict, List, Tuple

logger = get_logger(__name__)

class Naptha:
    """The entry point into Naptha."""

    def __init__(self,
            hub_url,
            node_url,
            routing_url=None,
            indirect_node_id=None,
            public_key=None,
            hub_username=None, 
            hub_password=None, 
            *args, 
            **kwargs
    ):
        
        self.public_key = public_key
        self.hub_username = hub_username
        self.hub_url = hub_url
        self.node_url = node_url
        self.routing_url = routing_url
        self.indirect_node_id = indirect_node_id
        self.node = Node(
            node_url=node_url,
            routing_url=routing_url,
            indirect_node_id=indirect_node_id
        )
        self.services = Services()
        self.hub = Hub(hub_url, public_key)  
        self.agents = []

    async def __aenter__(self):
        """Async enter method for context manager"""
        await self.hub.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async exit method for context manager"""
        await self.hub.close()

    def agent(self, name, worker_node_url):
        def decorator(func):
            self.agents.append(Agent(name=name, fn=func, worker_node_url=worker_node_url))
            return func
        return decorator

    async def publish(self):
        for agent in self.agents:
            logger.info(f"Publishing Agent Package...")

            agent_code, local_modules, installed_modules = scrape_code(agent.fn)

            agent_code = transform_code_agent(agent_code)
            create_poetry_package(agent.name)
            # add_dependency_to_pyproject(agent.name, used_classes)
            package_path = add_files_to_package(agent.name, agent_code, self.hub_username)
            success, response = await publish_ipfs_package(package_path)

            agent_config = {
                "name": agent.name,
                "description": agent.name,
                "author": f"user:{self.hub_username}",
                "url": f"ipfs://{response['ipfs_hash']}",
                "type": "package",
                "version": "0.1"
            }
            logger.info(f"Registering Agent {agent_config}")
            agent = await self.hub.create_agent(agent_config)
            logger.info(f"Published Agent: {agent}")


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