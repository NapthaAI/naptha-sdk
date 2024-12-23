import asyncio
from naptha_sdk.client.naptha import Naptha
from naptha_sdk.tool import Tool
from naptha_sdk.schemas import ToolDeployment, ToolRunInput

async def test_tool():
    naptha = Naptha()

    tool_deployment = ToolDeployment(
        module={"name": "generate_image_tool"},
        tool_node_url="http://localhost:7001"
    )

    tool = Tool(tool_deployment)

    input_params = {
        "tool_name": "generate_image_tool",
        "tool_input_data": "A beautiful image of a cat"
    }

    tool_run_input = ToolRunInput(
        consumer_id=naptha.user.id,
        inputs=input_params,
        tool_deployment=tool_deployment
    )

    response = await tool.call_tool_func(tool_run_input)

    print(response)

if __name__ == "__main__":
    asyncio.run(test_tool())