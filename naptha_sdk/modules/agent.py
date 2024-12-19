from dotenv import load_dotenv
from naptha_sdk.client.node import NodeClient
from naptha_sdk.schemas import AgentRunInput
from naptha_sdk.utils import get_logger

logger = get_logger(__name__)
load_dotenv(override=True)

class Agent:
    def __init__(self, 
        deployment, 
        *args,
        **kwargs
    ):
        self.deployment = deployment
        self.agent_node = NodeClient(self.deployment.node)

    async def call_agent_func(self, module_run_input: AgentRunInput, *args, **kwargs):
        logger.info(f"Running agent on worker node {self.agent_node.node_url}")
        
        agent_run = await self.agent_node.run_module(module_type="agent", run_input=module_run_input.model_dict())
        return agent_run
