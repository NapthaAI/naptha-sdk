from dotenv import load_dotenv
from huggingface_hub import HfApi, login
import inspect
from naptha_sdk.client.hub import Hub
from naptha_sdk.task_engine import run_task
import os
from naptha_sdk.utils import AsyncMixin

load_dotenv()

class Task(AsyncMixin):
    def __init__(self, name, fn, worker_node, orchestrator_node, flow_run):
        self.name = name
        self.fn = fn
        self.worker_node = worker_node
        self.orchestrator_node = orchestrator_node
        self.flow_run = flow_run
        super().__init__()

    async def __ainit__(self):
        await self.register_module()

    async def register_module(self):
        module_name = self.fn.__name__
        module_code = inspect.getsource(self.fn)
        with open(f'{module_name}.py', 'w') as file:
            file.write(module_code)

        hf_username = os.getenv("HF_USERNAME")
        login(os.getenv("HF_ACCESS_TOKEN"))
        api = HfApi()
        api.create_repo(repo_id=f"naptha_{module_name}")
        api.upload_file(
            path_or_fileobj=f'{module_name}.py',
            path_in_repo=f'{module_name}.py',
            repo_id=f"{hf_username}/naptha_{module_name}",
            repo_type="model",
        )
        module_config = {
            "name": module_name,
            "description": module_name,
            "author": "user:creator1",
            "url": f"https://huggingface.co/{hf_username}/naptha_{module_name}",
            "type": "template"
        }

        hub_url = os.getenv("HUB_URL")
        hub_username = os.getenv("HUB_USER")
        hub_password = os.getenv("HUB_PASS")
        hub = await Hub(hub_username, hub_password, hub_url)
        module = await hub.create_module(module_config)


    async def __call__(self, *args, **kwargs):
        return await run_task(task=self, flow_run=self.flow_run, parameters=kwargs)
    