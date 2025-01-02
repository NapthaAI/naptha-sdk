from naptha_sdk.client.node import Node
from naptha_sdk.schemas import AgentRun, ToolRunInput
from naptha_sdk.utils import get_logger, node_to_url
from naptha_sdk.user import sign_consumer_id
from typing import Union
from dotenv import load_dotenv
import os

logger = get_logger(__name__)
load_dotenv(override=True)
class Tool:
    def __init__(self, 
        tool_deployment,
        *args,
        **kwargs
    ):
        self.tool_deployment = tool_deployment
        self.tool_node = Node(self.tool_deployment.node)

    async def call_tool_func(self, module_run: Union[AgentRun, ToolRunInput]):
        logger.info(f"Running tool on worker node {self.tool_node}")

        tool_run_input = ToolRunInput(
            consumer_id=module_run.consumer_id,
            inputs=module_run.inputs,
            deployment=self.tool_deployment.model_dump(),
            signature=module_run.signature if module_run.signature else sign_consumer_id(module_run.consumer_id, os.getenv("PRIVATE_KEY"))
        )
        
        tool_run = await self.tool_node.run_tool_and_poll(tool_run_input)
        return tool_run