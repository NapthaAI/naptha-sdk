from datetime import datetime
import functools
import json
import os
import time
import traceback
import inspect
from naptha_sdk.code_extraction import create_poetry_package, transform_code_mas
from naptha_sdk.utils import get_logger, AsyncMixin, check_hf_repo_exists
from naptha_sdk.mas_engine import run_mas
from naptha_sdk.schemas import ModuleRunInput

logger = get_logger(__name__)

class MultiAgentService(AsyncMixin):
    def __init__(self, naptha, name, fn):
        self.naptha = naptha
        self.orchestrator_node = naptha.node.node_url
        self.name = name
        self.fn = fn
        super().__init__()

    async def __ainit__(self):
        logger.info(f"Registering multi-agent service...")
        self.module_name = await self.register_module()
        await self.register_service(self.module_name)

    async def register_module(self):
        module_name = self.fn.__name__
        mas_code = inspect.getsource(self.fn)
        mas_code = transform_code_mas(mas_code)
        create_poetry_package(module_name)
        with open(f'tmp/{module_name}/{module_name}/run.py', 'w') as file:
            file.write(mas_code)

        repo_id = f"mas_{module_name}"
        if not check_hf_repo_exists(self.naptha.hf, f"{self.naptha.hf_username}/{repo_id}"):
            logger.info(f"Creating HF repo {repo_id}")
            self.naptha.hf.create_repo(repo_id=repo_id)
        logger.info(f"Uploading folder to HF {f'tmp/{module_name}'}")
        self.naptha.hf.upload_folder(
            folder_path=f'tmp/{module_name}',
            repo_id=f"{self.naptha.hf_username}/{repo_id}",
            repo_type="model",
        )
        self.naptha.hf.create_tag(f"{self.naptha.hf_username}/{repo_id}", repo_type="model", tag="v0.1", exist_ok=True)
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
        mas_name = self.name

        mas_config = {
            "name": mas_name,
            "description": mas_name,
            "module_name": module_name,
            "worker_node_url": self.naptha.node.node_url,
        }
        logger.info(f"Registering Service {mas_config}")
        service = await self.naptha.hub.create_service(mas_config)

    async def __call__(self, run_params, worker_node_urls, *args, **kwargs):
        mas_run_input = {
            "name": self.name,
            "type": "template",
            "consumer_id": self.naptha.user["id"],
            "orchestrator_node": self.orchestrator_node,
            "worker_nodes": worker_node_urls,
            "module_name": self.module_name,
            "module_params": run_params,
        }
        mas_run_input = ModuleRunInput(**mas_run_input)
        return await run_mas(multi_agent_service=self, mas_run=mas_run_input)