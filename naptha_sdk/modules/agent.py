from dotenv import load_dotenv
from naptha_sdk.client.node import NodeClient, UserClient
from naptha_sdk.schemas import AgentRunInput, AgentDeployment
from naptha_sdk.utils import get_logger

logger = get_logger(__name__)
load_dotenv(override=True)

class Agent:
    def __init__(self, 
        deployment=None, 
        node_config=None,
        *args,
        **kwargs
    ):
        if deployment:
            self.deployment = deployment
            self.agent_node = UserClient(deployment.node)

        if node_config:
            self.agent_node = UserClient(node_config)

    async def call_agent_func(self, module_run_input: AgentRunInput, *args, **kwargs):
        logger.info(f"Running agent on worker node {self.agent_node.node_url}")
        agent_run = await self.agent_node.run_module(module_type="agent", run_input=module_run_input)
        return agent_run

    async def create(self, module_request: AgentDeployment):
        return await self.agent_node.create(module_type="agent", module_request=module_request)