import asyncio
from naptha_sdk.client.naptha import Naptha
from naptha_sdk.agent import Agent
from naptha_sdk.schemas import AgentDeployment, AgentRunInput

async def test_agent():
    naptha = Naptha()
    agent_deployment = AgentDeployment(
        module={"name": "simple_chat_agent"},
        worker_node_url="ws://localhost:7002"
    )
    agent = Agent(agent_deployment)

    input_params = {
        "tool_name": "chat",
        "tool_input_data": [{"role": "user", "content": "tell me a joke"}]
    }
    agent_run_input = AgentRunInput(
        consumer_id=naptha.user.id,
        inputs=input_params,
        agent_deployment=agent_deployment
    )
    response = await agent.call_agent_func(agent_run_input)
    print(response)
    
if __name__ == "__main__":
    asyncio.run(test_agent())