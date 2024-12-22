from naptha_sdk.client.node import Node
from naptha_sdk.schemas import AgentRunInput, OrchestratorRun, AgentDeployment
from naptha_sdk.utils import get_logger
from typing import Union

logger = get_logger(__name__)

class Agent:
    def __init__(self, agent_deployment: AgentDeployment):
        self.agent_deployment = agent_deployment

    async def call_agent_func(self, module_run: Union[OrchestratorRun, AgentRunInput], **kwargs):

        if isinstance(module_run, OrchestratorRun):
            worker_node_url = module_run.orchestrator_deployment.agent_deployments[self.agent_index].worker_node_url
            agent_run_input = AgentRunInput(
                consumer_id=self.orchestrator_run.consumer_id,
                inputs=kwargs,
                agent_deployment=self.orchestrator_run.orchestrator_deployment.agent_deployments[self.agent_index].model_dump(),
            )

        elif isinstance(module_run, AgentRunInput):
            worker_node_url = module_run.agent_deployment.worker_node_url
            agent_run_input = module_run
        else:
            raise ValueError("Invalid module run type")

        self.worker_node = Node(worker_node_url)

        self.worker_node.register_user(module_run.consumer_id)

        logger.info(f"Running agent on worker node {self.worker_node.node_url}")

        agent_run = await self.worker_node.run_agent_in_node(agent_run_input)
        return agent_run