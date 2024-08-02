from datetime import datetime
import functools
import json
import os
import time
import traceback
import inspect
from naptha_sdk.code_extraction import create_poetry_package, transform_code
from naptha_sdk.utils import AsyncMixin, check_hf_repo_exists

class MultiAgentService(AsyncMixin):
    def __init__(self, naptha, name, fn):
        self.naptha = naptha
        self.name = name
        self.fn = fn
        super().__init__()

    async def __ainit__(self):
        module_name = await self.register_module()
        await self.register_service(module_name)

    async def register_module(self):
        module_name = self.fn.__name__
        mas_code = inspect.getsource(self.fn)
        mas_code = transform_code(mas_code)
        create_poetry_package(module_name)
        with open(f'tmp/{module_name}/{module_name}/run.py', 'w') as file:
            file.write(mas_code)

        repo_id = f"mas_{module_name}"
        if not check_hf_repo_exists(self.naptha.hf, f"{self.naptha.hf_username}/{repo_id}"):
            self.naptha.hf.create_repo(repo_id=repo_id)
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
        service = await self.naptha.hub.create_service(mas_config)


