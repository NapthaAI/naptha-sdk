from naptha_sdk.client.node import NodeClient, UserClient
from naptha_sdk.schemas import AgentDeployment, AgentRunInput
from naptha_sdk.utils import get_logger
from naptha_sdk.schemas import SecretInput
from typing import List

logger = get_logger(__name__)

class Agent:
    async def create(self, deployment: AgentDeployment, *args, **kwargs):
        logger.info(f"Creating agent on worker node {deployment.node}")
        node = UserClient(deployment.node)
        agent_deployment = await node.create(module_type="agent", module_request=deployment)
        return agent_deployment

    async def run(self, module_run_input: AgentRunInput, secrets: List[SecretInput] = [], *args, **kwargs):
        logger.info(f"Running agent on worker node {module_run_input.deployment.node}")
        node = NodeClient(module_run_input.deployment.node)
        agent_run = await node.run_module(module_type="agent", run_input=module_run_input, secrets=secrets)
        return agent_run