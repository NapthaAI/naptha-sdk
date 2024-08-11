import inspect
import os
from naptha_sdk.agent_service_engine import run_agent_service
from naptha_sdk.code_extraction import create_poetry_package, publish_hf_package, transform_code_as
from naptha_sdk.schemas import ModuleRunInput
from naptha_sdk.utils import get_logger, AsyncMixin

logger = get_logger(__name__)

class AgentService(AsyncMixin):
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

    async def __ainit__(self):
        self.publish_package()
        await self.register_module()
        await self.register_service()

    def publish_package(self, naptha):
        logger.info(f"Publishing Package...")
        as_code = inspect.getsource(self.fn)
        as_code = transform_code_as(as_code)
        create_poetry_package(self.module_name)
        publish_hf_package(naptha.hf, self.module_name, self.repo_id, as_code, naptha.hf_username)

    async def register_module(self, naptha):
        module_config = {
            "name": self.module_name,
            "description": self.module_name,
            "author": f"user:{naptha.hf_username}",
            "url": f"https://huggingface.co/{naptha.hf_username}/{self.repo_id}",
            "type": "template"
        }
        logger.info(f"Registering Agent Module {module_config}")
        module = await naptha.hub.create_module(module_config)

    async def register_service(self, naptha):
        agent_service_name = self.name
        agent_service_config = {
            "name": agent_service_name,
            "description": agent_service_name,
            "module_name": self.module_name,
            "worker_node_url": self.worker_node.node_url,
        }
        logger.info(f"Registering Agent Service {agent_service_config}")
        service = await naptha.hub.create_service(agent_service_config)

    async def __call__(self, *args, **kwargs):
        return await run_agent_service(agent_service=self, flow_run=self.flow_run, parameters=kwargs)
