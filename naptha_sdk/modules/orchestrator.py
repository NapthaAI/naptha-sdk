from naptha_sdk.client.node import NodeClient, UserClient
from naptha_sdk.schemas import OrchestratorDeployment, OrchestratorRunInput
from naptha_sdk.utils import get_logger

logger = get_logger(__name__)

class Orchestrator:
    async def create(self, deployment: OrchestratorDeployment, *args, **kwargs):
        logger.info(f"Creating orchestrator on worker node {deployment.node}")
        node = UserClient(deployment.node)
        orchestrator_deployment = await node.create(module_type="orchestrator", module_request=deployment)
        return orchestrator_deployment

    async def run(self, module_run_input: OrchestratorRunInput, *args, **kwargs):
        logger.info(f"Running orchestrator on worker node {module_run_input.deployment.node}")
        node = NodeClient(module_run_input.deployment.node)
        orchestrator_run = await node.run_module(module_type="orchestrator", run_input=module_run_input)
        return orchestrator_run