from naptha_sdk.client.node import NodeClient
from naptha_sdk.schemas import EnvironmentDeployment, EnvironmentRunInput
from typing import Any, Dict, List
import logging

logger = logging.getLogger(__name__)

class Environment:
    def __init__(self, environment_deployment: EnvironmentDeployment):
        self.environment_deployment = environment_deployment
        self.environment_node = NodeClient(self.environment_deployment.node)

    async def call_environment_func(self, module_run: EnvironmentRunInput):
        logger.info(f"Running environment on environment node {self.environment_node}")
        environment_run = await self.environment_node.run_module(module_type="environment", run_input=module_run)
        return environment_run
