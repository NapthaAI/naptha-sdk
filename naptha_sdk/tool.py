from naptha_sdk.client.node import Node
from naptha_sdk.schemas import AgentRun, ToolRunInput
from naptha_sdk.utils import get_logger
from typing import Union

logger = get_logger(__name__)

class Tool:
    def __init__(self, 
        tool_deployment,
        *args,
        **kwargs
    ):
        self.tool_deployment = tool_deployment
        print("FFFFF", self.tool_deployment)
        self.tool_node = Node(self.tool_deployment.tool_node_url)

    async def call_tool_func(self, module_run: Union[AgentRun, ToolRunInput]):
        logger.info(f"Running tool on worker node {self.tool_node.node_url}")

        print("GGGGG", self.tool_deployment)

        tool_run_input = ToolRunInput(
            consumer_id=module_run.consumer_id,
            inputs=module_run.inputs,
            tool_deployment=self.tool_deployment,
        )
        
        tool_run = await self.tool_node.run_tool_and_poll(tool_run_input)
        return tool_run