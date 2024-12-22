from naptha_sdk.schemas import OrchestratorDeployment, OrchestratorRunInput, OrchestratorRun
from naptha_sdk.client.node import Node


class Orchestrator:
    def __init__(self, orchestrator_deployment: OrchestratorDeployment):
        self.orchestrator_deployment = orchestrator_deployment
    

    async def call_orchestrator_func(self, input: OrchestratorRunInput) -> OrchestratorRun:
        node = Node(self.orchestrator_deployment.environment_deployments[0].environment_node_url)
        orchestrator_run = await node.run_orchestrator(input)
        return orchestrator_run