from naptha_sdk.utils import get_logger

logger = get_logger(__name__)

class MultiAgentService():
    def __init__(self, naptha, name, fn):
        self.naptha = naptha
        self.name = name
        self.fn = fn
        self.orchestrator_node = naptha.node.node_url
        self.module_name = self.fn.__name__
        self.repo_id = f"mas_{self.module_name}"
        super().__init__()
