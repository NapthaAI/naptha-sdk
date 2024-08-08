import inspect
import os
from naptha_sdk.code_extraction import create_poetry_package, transform_code
from naptha_sdk.utils import get_logger, AsyncMixin, check_hf_repo_exists

logger = get_logger(__name__)

class AgentService(AsyncMixin):
    def __init__(self, naptha, name, fn, worker_node_url):
        self.name = name
        self.fn = fn
        self.worker_node_url = worker_node_url
        self.naptha = naptha
        super().__init__()

    async def __ainit__(self):
        module_name = await self.register_module()
        await self.register_service(module_name)

    async def register_module(self):
        module_name = self.fn.__name__
        module_code = inspect.getsource(self.fn)
        module_code = transform_code(module_code)
        create_poetry_package(module_name)
        with open(f'tmp/{module_name}/{module_name}/run.py', 'w') as file:
            file.write(module_code)

        repo_id = f"as_{module_name}"
        if not check_hf_repo_exists(self.naptha.hf, f"{self.naptha.hf_username}/{repo_id}"):
            logger.info(f"Creating HF repo {repo_id}")
            self.naptha.hf.create_repo(repo_id=repo_id)
            logger.info(f"Uploading folder to HF {f'tmp/{module_name}'}")
            self.naptha.hf.upload_folder(
                folder_path=f'tmp/{module_name}',
                repo_id=f"{self.naptha.hf_username}/{repo_id}",
                repo_type="model",
            )
        module_config = {
            "name": module_name,
            "description": module_name,
            "author": f"user:{self.naptha.hf_username}",
            "url": f"https://huggingface.co/{self.naptha.hf_username}/{repo_id}",
            "type": "template"
        }
        logger.info(f"Registering Module {module_config}")
        module = await self.naptha.hub.create_module(module_config)
        return module_name

    async def register_service(self, module_name):
        agent_service_name = self.name

        agent_service_config = {
            "name": agent_service_name,
            "description": agent_service_name,
            "module_name": module_name,
            "worker_node_url": self.worker_node_url,
        }
        logger.info(f"Registering Service {agent_service_config}")
        service = await self.naptha.hub.create_service(agent_service_config)

    async def __call__(self, *args, **kwargs):
        return await run_agent_service(agent_service=self, mas_run=self.mas_run, parameters=kwargs)
    