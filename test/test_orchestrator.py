

from naptha_sdk.client.naptha import Naptha
from naptha_sdk.schemas import OrchestratorDeployment, OrchestratorRunInput, EnvironmentDeployment
from naptha_sdk.orchestrator import Orchestrator
import asyncio


async def test_orchestrator():
    naptha = Naptha()
    orchestrator_deployment = OrchestratorDeployment(
        module={"name": "multiagent_chat"},
        orchestrator_node_url="http://localhost:7001",
        environment_deployments=[EnvironmentDeployment(environment_node_url="http://localhost:7001")]
    )
    orchestrator = Orchestrator(orchestrator_deployment)
    
    input_params = {
        "tool_name": "chat",
        "tool_input_data": [{"role": "user", "content": "i would like to count up to ten, one number at a time. ill start. one."}]
    }
    orchestrator_run_input = OrchestratorRunInput(
        consumer_id=naptha.user.id,
        inputs=input_params,
        orchestrator_deployment=orchestrator_deployment
    )
    response = await orchestrator.call_orchestrator_func(orchestrator_run_input)
    print(response)

    
if __name__ == "__main__":
    asyncio.run(test_orchestrator())