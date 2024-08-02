import inspect
import os
from naptha_sdk.code_extraction import create_poetry_package, transform_code
from naptha_sdk.utils import AsyncMixin, check_hf_repo_exists


class AgentService(AsyncMixin):
    def __init__(self, naptha, name, fn, worker_node, orchestrator_node):
        self.name = name
        self.fn = fn
        self.worker_node = worker_node
        self.orchestrator_node = orchestrator_node
        self.naptha = naptha
        super().__init__()

    async def __ainit__(self):
        await self.register_module()

    async def register_module(self):

        agent_service_name = self.fn.__name__
        agent_service_code = inspect.getsource(self.fn)
        agent_service_code = transform_code(agent_service_code)
        create_poetry_package(agent_service_name)
        with open(f'{agent_service_name}/{agent_service_name}/run.py', 'w') as file:
            file.write(agent_service_code)

        repo_id = f"as_{agent_service_name}"
        if not check_hf_repo_exists(self.naptha.hf, repo_id):
            self.naptha.hf.create_repo(repo_id=repo_id)
            self.naptha.hf.upload_folder(
                folder_path=agent_service_name,
                repo_id=f"{self.naptha.hf_username}/{repo_id}",
                repo_type="model",
            )
        agent_service_config = {
            "name": agent_service_name,
            "description": agent_service_name,
            "author": f"user:{self.naptha.hf_username}",
            "url": f"https://huggingface.co/{self.naptha.hf_username}/{repo_id}",
            "type": "template"
        }
        module = await self.naptha.hub.create_module(agent_service_config)

