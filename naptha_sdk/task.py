from dotenv import load_dotenv
import inspect
from naptha_sdk.client.hub import Hub
from naptha_sdk.task_engine import run_task
import os
from naptha_sdk.utils import AsyncMixin

load_dotenv()

class Task(AsyncMixin):
    def __init__(self, name, fn, worker_node, orchestrator_node, flow_run, naptha=None):
        self.name = name
        self.fn = fn
        self.worker_node = worker_node
        self.orchestrator_node = orchestrator_node
        self.flow_run = flow_run
        self.naptha = naptha
        super().__init__()

    async def __ainit__(self):
        await self.register_module()

    async def register_module(self):
        module_name = self.fn.__name__
        module_code = inspect.getsource(self.fn)
        with open(f'{module_name}.py', 'w') as file:
            file.write(module_code)

        self.naptha.hf.create_repo(repo_id=f"naptha_{module_name}")
        self.naptha.hf.upload_file(
            path_or_fileobj=f'{module_name}.py',
            path_in_repo=f'{module_name}.py',
            repo_id=f"{self.naptha.hf_username}/naptha_{module_name}",
            repo_type="model",
        )
        module_config = {
            "name": module_name,
            "description": module_name,
            "author": "user:creator1",
            "url": f"https://huggingface.co/{self.naptha.hf_username}/naptha_{module_name}",
            "type": "template"
        }
        module = await self.naptha.hub.create_module(module_config)


    async def __call__(self, *args, **kwargs):
        return await run_task(task=self, flow_run=self.flow_run, parameters=kwargs)
    