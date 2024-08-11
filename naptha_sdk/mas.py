from datetime import datetime
import functools
import json
import os
import time
import traceback
import inspect
from naptha_sdk.code_extraction import create_poetry_package, publish_hf_package, transform_code_mas
from naptha_sdk.utils import get_logger, AsyncMixin
from naptha_sdk.mas_engine import run_mas
from naptha_sdk.schemas import ModuleRunInput

logger = get_logger(__name__)

class MultiAgentService(AsyncMixin):
    def __init__(self, naptha, name, fn):
        self.naptha = naptha
        self.name = name
        self.fn = fn
        self.orchestrator_node = naptha.node.node_url
        self.module_name = self.fn.__name__
        self.repo_id = f"mas_{self.module_name}"
        super().__init__()

    async def __ainit__(self):
        self.publish_package()
        await self.register_module()
        await self.register_service()

    def publish_package(self):
        logger.info(f"Publishing Package...")
        mas_code = inspect.getsource(self.fn)
        mas_code = transform_code_mas(mas_code)
        create_poetry_package(self.module_name)
        publish_hf_package(self.naptha.hf, self.module_name, self.repo_id, mas_code, self.naptha.hf_username)

    async def register_module(self):
        module_config = {
            "name": self.module_name,
            "description": self.module_name,
            "author": f"user:{self.naptha.hf_username}",
            "url": f"https://huggingface.co/{self.naptha.hf_username}/{self.repo_id}",
            "type": "template"
        }
        logger.info(f"Registering Multi-Agent Module {module_config}")
        module = await self.naptha.hub.create_module(module_config)

    async def register_service(self):
        mas_name = self.name
        mas_config = {
            "name": mas_name,
            "description": mas_name,
            "module_name": self.module_name,
            "worker_node_url": self.naptha.node.node_url,
        }
        logger.info(f"Registering Multi-Agent Service {mas_config}")
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