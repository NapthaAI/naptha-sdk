from naptha_sdk.client.node import NodeClient, UserClient
from naptha_sdk.schemas import AgentRun, ToolRunInput, ToolDeployment
from naptha_sdk.utils import get_logger
from typing import Union
from naptha_sdk.schemas import SecretInput
from typing import List

logger = get_logger(__name__)

class Tool:
    async def create(self, deployment: ToolDeployment, *args, **kwargs):
        logger.info(f"Creating tool on worker node {deployment.node}")
        node = UserClient(deployment.node)
        tool_deployment = await node.create(module_type="tool", module_request=deployment)
        return tool_deployment

    async def run(self, module_run_input: Union[AgentRun, ToolRunInput], secrets: List[SecretInput] = []):
        logger.info(f"Running tool on worker node {module_run_input.deployment.node}")
        node = NodeClient(module_run_input.deployment.node)
        tool_run = await node.run_module(module_type="tool", run_input=module_run_input, secrets=secrets)
        return tool_run