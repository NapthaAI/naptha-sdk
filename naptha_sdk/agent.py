from naptha_sdk.client.node import Node
from naptha_sdk.schemas import AgentRunInput
from naptha_sdk.utils import get_logger

logger = get_logger(__name__)

class Agent:
    def __init__(self, 
        orchestrator_run, 
        agent_index,
        *args,
        **kwargs
    ):
        self.orchestrator_run = orchestrator_run
        self.agent_index = agent_index
        self.worker_node = None

    async def initialize(self):
        """Initialize the agent by setting up the worker node connection"""
        worker_node_url = self.orchestrator_run.agent_deployments[self.agent_index].worker_node_url
        worker_node_url = await self.identify_communication_type(worker_node_url)
        self.worker_node = Node(worker_node_url)

    async def identify_communication_type(self, agent_node_url):
        if "ws://" in agent_node_url:
            return agent_node_url
        elif "grpc://" in agent_node_url:
            return agent_node_url
        else:
            # Create temporary node for health check
            temp_node = Node(f"http://{agent_node_url}")
            ws_health_url = f"http://{agent_node_url}/health"

            try:
                ws_health = await temp_node.check_health_ws(ws_health_url)
                return f"ws://{agent_node_url}" if ws_health else f"grpc://{agent_node_url}"
            except Exception as e:
                logger.error(f"Error checking node health: {e}")
                raise

    async def call_agent_func(self, *args, **kwargs):
        if self.worker_node is None:
            await self.initialize()
            
        logger.info(f"Running agent on worker node {self.worker_node.node_url}")

        agent_run_input = AgentRunInput(
            consumer_id=self.orchestrator_run.consumer_id,
            inputs=kwargs,
            agent_deployment=self.orchestrator_run.agent_deployments[self.agent_index].model_dump(),
        )
        
        try:
            agent_run = await self.worker_node.run_agent_in_node(agent_run_input)
            return agent_run
        except Exception as e:
            logger.error(f"Error running agent: {e}")
            raise