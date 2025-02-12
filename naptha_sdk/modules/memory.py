from naptha_sdk.client.node import NodeClient, UserClient
from naptha_sdk.schemas import AgentRun, MemoryRunInput, MemoryDeployment
from naptha_sdk.utils import get_logger
from typing import Union

logger = get_logger(__name__)

class Memory:
    async def create(self, deployment: MemoryDeployment, *args, **kwargs):
        logger.info(f"Creating memory on worker node {deployment.node}")
        node = UserClient(deployment.node)
        memory_deployment = await node.create(module_type="memory", module_request=deployment)
        return memory_deployment

    async def run(self, module_run_input: Union[AgentRun, MemoryRunInput]):
        logger.info(f"Running memory module on worker node {module_run_input.deployment.node}")
        node = NodeClient(module_run_input.deployment.node)
        memory_run = await node.run_module(module_type="memory", run_input=module_run_input)
        return memory_run