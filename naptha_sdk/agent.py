from naptha_sdk.client.node import Node
from naptha_sdk.utils import get_logger

logger = get_logger(__name__)

class Agent:
    def __init__(self, 
        name, 
        module, 
        worker_node_url,
        user,
    ):
        self.name = name
        self.module = module
        self.user = user
        if isinstance(worker_node_url, str):
            self.worker_node = Node(worker_node_url)
        else:
            self.worker_node = worker_node_url

    async def call_agent_func(self, *args, **kwargs):
        logger.info(f"Running agent on worker node {self.worker_node.node_url}")

        agent_run_input = {
            "consumer_id": self.user.id,
            "worker_nodes": [self.worker_node.node_url],
            "agent_name": self.module,
            "agent_run_type": "package",
            "agent_run_params": kwargs,
        }

        agent_run = await self.worker_node.run_agent(agent_run_input=agent_run_input)
    