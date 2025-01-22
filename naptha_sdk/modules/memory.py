from naptha_sdk.client.node import NodeClient
from naptha_sdk.schemas import AgentRun, MemoryRunInput
from naptha_sdk.utils import get_logger
from typing import Union
from dotenv import load_dotenv
import os

logger = get_logger(__name__)
load_dotenv(override=True)
class Memory:
    def __init__(self, 
        deployment,
        *args,
        **kwargs
    ):
        self.deployment = deployment
        self.node_client = NodeClient(self.deployment.node)

    async def run_module(self, module_run: Union[AgentRun, MemoryRunInput]):
        logger.info(f"Running memory module on worker node {self.deployment.node}")
        memory_run = await self.node_client.run_module(module_type="memory", run_input=module_run.model_dict())
        return memory_run