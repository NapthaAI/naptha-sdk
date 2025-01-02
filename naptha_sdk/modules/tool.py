from naptha_sdk.client.node import NodeClient
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
        self.tool_node = NodeClient(self.tool_deployment.node)

    async def call_tool_func(self, module_run: Union[AgentRun, ToolRunInput]):
        logger.info(f"Running tool on worker node {self.tool_node}")

        tool_run_input = ToolRunInput(
            consumer_id=module_run.consumer_id,
            inputs=module_run.inputs.model_dump(),
            deployment=self.tool_deployment.model_dump(),
        )
        tool_run = await self.tool_node.run_module(module_type="tool", run_input=tool_run_input.model_dump())
        return tool_run