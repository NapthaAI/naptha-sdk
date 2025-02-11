import logging
from naptha_sdk.client.node import NodeClient, UserClient
from naptha_sdk.schemas import EnvironmentDeployment, EnvironmentRunInput

logger = logging.getLogger(__name__)

class Environment:
    async def create(self, deployment: EnvironmentDeployment, *args, **kwargs):
        logger.info(f"Creating environment on worker node {deployment.node}")
        node = UserClient(deployment.node)
        environment_run = await node.create(module_type="environment", module_request=deployment)
        return environment_run

    async def run(self, module_run_input: EnvironmentRunInput):
        logger.info(f"Running environment on environment node {module_run_input.deployment.node}")
        node = NodeClient(module_run_input.deployment.node)
        environment_run = await node.run_module(module_type="environment", run_input=module_run_input)
        return environment_run
