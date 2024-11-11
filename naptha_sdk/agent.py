from naptha_sdk.client.node import Node
from naptha_sdk.utils import get_logger

logger = get_logger(__name__)

class Agent:
    def __init__(self, 
        name, 
        fn, 
        worker_node_url,
        orchestrator_node, 
        flow_run, 
        cfg,
        task_engine_cls,
        node_cls,
        **kwargs
    ):
        self.name = name
        self.fn = fn
        self.orchestrator_node = orchestrator_node
        self.flow_run = flow_run
        self.task_engine_cls = task_engine_cls
        if isinstance(worker_node_url, str):
            self.worker_node = self.node_url_to_node(worker_node_url, node_cls)
        else:
            self.worker_node = worker_node_url

    async def call_agent_func(self, *args, **kwargs):
        logger.info(f"Running agent on worker node {self.worker_node.node_url}")

        agent_run_input = {
            "consumer_id": self.flow_run.consumer_id,
            "worker_nodes": [self.worker_node.node_url],
            "agent_name": self.fn,
            "agent_run_type": "package",
            "agent_run_params": kwargs,
        }

        agent_run = await self.worker_node.run_agent(agent_run_input=agent_run_input)
        return agent_run
    
    def node_url_to_node(self, node_url, node_cls):
        if 'ws://' in node_url:
            return node_cls(node_url, 'ws')
        elif 'http://' in node_url:
            return node_cls(node_url, 'http')
        elif '://' not in node_url:
            return node_cls(node_url, 'grpc')
        else:
            raise ValueError(f"Invalid node URL: {node_url}")