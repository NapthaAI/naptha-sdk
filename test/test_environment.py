import asyncio
from naptha_sdk.client.naptha import Naptha
from naptha_sdk.environment import Environment, EnvironmentDeployment, EnvironmentRunInput


async def test_environment():

    naptha = Naptha()

    environment_deployment = EnvironmentDeployment(
        module={"name": "groupchat_environment"},
        environment_node_url="http://localhost:7001"
    )

    environment = Environment(environment_deployment)

    input_params = {
        "function_name": "get_global_state",
        "function_input_data": None,
    }

    environment_run_input = EnvironmentRunInput(
        consumer_id=naptha.user.id,
        inputs=input_params,
        environment_deployment=environment_deployment
    )

    response = await environment.call_environment_func(environment_run_input)

    print(response)

if __name__ == "__main__":
    asyncio.run(test_environment())
