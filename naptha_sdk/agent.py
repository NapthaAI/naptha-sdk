from naptha_sdk.client.node import Node
from naptha_sdk.schemas import AgentRunInput, OrchestratorDeployment
from naptha_sdk.utils import get_logger

logger = get_logger(__name__)


class Agent:
    def __init__(self,
                 orchestrator_deployment: OrchestratorDeployment,
                 agent_index: int
                 ):
        self.orchestrator_deployment = orchestrator_deployment
        self.agent_index = agent_index
        worker_node_url = self.orchestrator_deployment.agent_deployments[self.agent_index].worker_node_url
        self.worker_node = Node(worker_node_url)

    async def create(self):
        logger.info(f"Creating agent on worker node {self.worker_node.node_url}")
        return await self.worker_node.create("agent", self.orchestrator_deployment.agent_deployments[self.agent_index])

    async def call_agent_func(self, agent_run_input: AgentRunInput):
        logger.info(f"Running agent on worker node {self.worker_node.node_url}")

        agent_run = await self.worker_node.run_agent_in_node(agent_run_input)
        return agent_run
