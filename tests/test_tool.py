import asyncio
from naptha_sdk.client.naptha import Naptha
from naptha_sdk.modules.tool import Tool
from naptha_sdk.schemas import ToolDeployment, ToolRunInput, NodeConfigUser
from naptha_sdk.user import sign_consumer_id
from dotenv import load_dotenv
import os

load_dotenv(override=True)

async def test_tool():
    naptha = Naptha()

    tool_deployment = ToolDeployment(
        module={"name": "generate_image_tool"},
        node=NodeConfigUser(
            ip="localhost",
            http_port=7001,
            server_type="http"
        )
    )

    tool = Tool(tool_deployment)

    input_params = {
        "tool_name": "generate_image_tool",
        "tool_input_data": "A beautiful image of a cat"
    }

    tool_run_input = ToolRunInput(
        consumer_id=naptha.user.id,
        inputs=input_params,
        deployment=tool_deployment,
        signature=sign_consumer_id(naptha.user.id, os.getenv("PRIVATE_KEY"))
    )

    response = await tool.call_tool_func(tool_run_input)

    print(response)

if __name__ == "__main__":
    asyncio.run(test_tool())