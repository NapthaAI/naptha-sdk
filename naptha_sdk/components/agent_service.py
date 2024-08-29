from naptha_sdk.agent_service_engine import run_agent_service
from naptha_sdk.utils import get_logger

logger = get_logger(__name__)

class AgentService():
    def __init__(self, name, fn, worker_node, orchestrator_node, flow_run=None):
        self.name = name
        self.fn = fn
        if isinstance(self.fn, str):
            self.module_name = self.fn
        else:
            self.module_name = self.fn.__name__
        self.worker_node = worker_node
        self.orchestrator_node = orchestrator_node
        self.flow_run = flow_run
        self.repo_id = f"as_{self.module_name}"
        super().__init__()

    async def __call__(self, *args, **kwargs):
        return await run_agent_service(agent_service=self, flow_run=self.flow_run, parameters=kwargs)
