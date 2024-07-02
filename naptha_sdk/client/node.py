from typing import Dict, Optional
from naptha_sdk.schemas import ModuleRun, ModuleRunInput
from naptha_sdk.client.comms.http_client import (
    check_user_http, register_user_http, run_task_http, check_tasks_http, check_task_http, 
    create_task_run_http, update_task_run_http, read_storage_http, write_storage_http
)
from naptha_sdk.client.comms.ws_client import (
    check_user_ws, register_user_ws, run_task_ws, check_task_ws, 
    create_task_run_ws, update_task_run_ws, read_storage_ws, write_storage_ws
)
from naptha_sdk.utils import get_logger


logger = get_logger(__name__)

class Node:
    def __init__(self, node_url: Optional[str] = None, indirect_node_id: Optional[str] = None, routing_url: Optional[str] = None):
        self.node_url = node_url
        self.indirect_node_id = indirect_node_id
        self.routing_url = routing_url

        # at least one of node_url and indirect_node_id must be set
        if not node_url and not indirect_node_id:
            raise ValueError("Either node_url or indirect_node_id must be set")
        
        # if indirect_node_id is set, we need the routing_url to be set
        if indirect_node_id and not routing_url:
            raise ValueError("routing_url must be set if indirect_node_id is set")
        
        if self.node_url:
            self.client = 'http'
            logger.info("Using http client")
            logger.info(f"Node URL: {self.node_url}")
        else:
            self.client = 'ws'
            logger.info("Using ws client")
            logger.info(f"Routing URL: {self.routing_url}")
            logger.info(f"Indirect Node ID: {self.indirect_node_id}")
        
        self.access_token = None


    async def check_user(self, user_input):
        if self.client == 'http':
            return await check_user_http(self.node_url, user_input)
        else:
            return await check_user_ws(self.routing_url, self.indirect_node_id, user_input)


    async def register_user(self, user_input):
        if self.client == 'http':
            return await register_user_http(self.node_url, user_input)
        else:
            return await register_user_ws(self.routing_url, self.indirect_node_id, user_input)

    async def run_task(self, module_run_input: ModuleRunInput) -> ModuleRun:
        if self.client == 'http':
            return await run_task_http(
                node_url=self.node_url,
                module_run_input=module_run_input,
                access_token=self.access_token
            )
        else:
            return await run_task_ws(
                routing_url=self.routing_url,
                indirect_node_id=self.indirect_node_id,
                module_run_input=module_run_input
            )

    async def check_tasks(self):
        if self.client == 'http':
            return await check_tasks_http(self.node_url)
        else:
            raise NotImplementedError("check_tasks is not implemented for ws client")

    async def check_task(self, module_run: ModuleRun) -> ModuleRun:
        if self.client == 'http':
            return await check_task_http(self.node_url, module_run)
        else:
            return await check_task_ws(self.routing_url, self.indirect_node_id, module_run)

    async def create_task_run(self, module_run_input: ModuleRunInput) -> ModuleRun:
        if self.client == 'http':
            logger.info(f"Creating task run with input: {module_run_input}")
            logger.info(f"Node URL: {self.node_url}")
            return await create_task_run_http(self.node_url, module_run_input)
        else:
            return await create_task_run_ws(self.routing_url, self.indirect_node_id, module_run_input)

    async def update_task_run(self, module_run: ModuleRun):
        if self.client == 'http':
            return await update_task_run_http(self.node_url, module_run)
        else:
            return await update_task_run_ws(self.routing_url, self.indirect_node_id, module_run)

    async def read_storage(self, module_run_id, output_dir, ipfs=False):
        if self.client == 'http':
            return await read_storage_http(self.node_url, module_run_id, output_dir, ipfs)
        else:
            return await read_storage_ws(self.routing_url, self.indirect_node_id, module_run_id, output_dir, ipfs)
    
    async def write_storage(self, storage_input: str, ipfs: bool = False) -> Dict[str, str]:
        if self.client == 'http':
            return await write_storage_http(self.node_url, storage_input, ipfs)
        else:
            return await write_storage_ws(self.routing_url, self.indirect_node_id, storage_input, ipfs)