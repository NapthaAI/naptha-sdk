import json
import os
import shutil
import tempfile
import time
import traceback
import uuid
import zipfile
import random
from pathlib import Path
from typing import Dict, Optional, Any, List, Tuple, Union

import grpc
import httpx
import websockets
from google.protobuf import struct_pb2
from google.protobuf.json_format import MessageToDict
from httpx import HTTPStatusError, RemoteProtocolError

from naptha_sdk.client import grpc_server_pb2
from naptha_sdk.client import grpc_server_pb2_grpc
from naptha_sdk.schemas import AgentRun, AgentRunInput, ChatCompletionRequest, EnvironmentRun, EnvironmentRunInput, OrchestratorRun, \
    OrchestratorRunInput, AgentDeployment, EnvironmentDeployment, OrchestratorDeployment, KBDeployment, KBRunInput, KBRun, ToolRunInput, ToolRun, NodeConfig, NodeConfigUser, ModelResponse, ToolDeployment
from naptha_sdk.utils import get_logger, node_to_url

logger = get_logger(__name__)
HTTP_TIMEOUT = 300

class NodeClient:
    def __init__(self, node: NodeConfig):
        self.node = node
        self.server_type = node.server_type
        self.node_url = self.node_to_url(node)
        self.connections = {}

        self.access_token = None
        logger.info(f"Node URL: {self.node_url}")

    def node_to_url(self, node: NodeConfig):
        ports = node.ports
        if len(ports) == 0:
            raise ValueError("No ports found for node")
        if node.server_type == 'ws':
            return f"ws://{node.ip}:{random.choice(ports)}"
        elif node.server_type == 'grpc':
            return f"{node.ip}:{random.choice(ports)}"
        else:
            raise ValueError("Invalid server type. Server type must be either 'ws' or 'grpc'.")

    async def check_user(self, user_input: Dict[str, str]) -> Dict[str, Any]:
        if self.node.server_type == 'ws':
            return await self.check_user_ws(user_input)
        elif self.node.server_type == 'grpc':
            return await self.check_user_grpc(user_input)
        else:
            raise ValueError("Invalid server type. Server type must be either 'ws' or 'grpc'.")

    async def check_user_ws(self, user_input: Dict[str, str]):
        response = await self.send_receive_ws(user_input, "user/check")
        logger.info(f"Check user response: {response}")
        return response

    async def check_user_grpc(self, user_input: Dict[str, str]):
        async with grpc.aio.insecure_channel(self.node_url) as channel:
            stub = grpc_server_pb2_grpc.GrpcServerStub(channel)
            request = grpc_server_pb2.CheckUserRequest(
                user_id=user_input.get('user_id', ''),
                public_key=user_input.get('public_key', '')
            )
            response = await stub.CheckUser(request)
            logger.info(f"Check user response: {response}")
            return MessageToDict(response, preserving_proto_field_name=True)

    async def register_user(self, user_input: Dict[str, str]) -> Dict[str, Any]:
        if self.node.server_type == 'ws':
            return await self.register_user_ws(user_input)
        elif self.node.server_type == 'grpc':
            return await self.register_user_grpc(user_input)
        else:
            raise ValueError("Invalid server type. Server type must be either 'ws' or 'grpc'.")
        
    async def register_user_ws(self, user_input: Dict[str, str]):
        response = await self.send_receive_ws(user_input, "user/register")
        logger.info(f"Register user response: {response}")
        return response

    async def register_user_grpc(self, user_input: Dict[str, str]):
        async with grpc.aio.insecure_channel(self.node_url) as channel:
            stub = grpc_server_pb2_grpc.GrpcServerStub(channel)
            request = grpc_server_pb2.RegisterUserRequest(
                public_key=user_input.get('public_key', '')
            )
            response = await stub.RegisterUser(request)
            return {
                'id': response.id,
                'public_key': response.public_key,
            }

    async def run_module(self, module_type: str, run_input: Union[AgentRunInput, KBRunInput, ToolRunInput, EnvironmentRunInput]):
        if self.node.server_type == 'ws':
            return await self.run_module_ws(module_type, run_input)
        elif self.node.server_type == 'grpc':
            return await self.run_module_grpc(module_type, run_input)
        else:
            raise ValueError("Invalid server type. Server type must be either 'ws' or 'grpc'.")

    async def run_module_ws(self, module_type: str, run_input):
        response = await self.send_receive_ws(run_input, f"{module_type}/run")
        
        output_types = {
            "agent": AgentRun,
            "kb": KBRun,
            "tool": ToolRun,
            "environment": EnvironmentRun
        }
        
        if response['status'] == 'success':
            return output_types[module_type](**response['data'])
        else:
            logger.error(f"Error running {module_type}: {response['message']}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            raise Exception(response['message'])

    async def run_module_grpc(self, module_type: str, run_input):
        async with grpc.aio.insecure_channel(self.node_url) as channel:
            stub = grpc_server_pb2_grpc.GrpcServerStub(channel)

            # Convert inputs to Struct
            input_struct = struct_pb2.Struct()
            if run_input.inputs:
                if isinstance(run_input.inputs, dict):
                    input_data = run_input.inputs.dict() if hasattr(run_input.inputs, 'dict') else run_input.inputs
                    input_struct.update(input_data)

            # Create node config
            node_config = grpc_server_pb2.NodeConfigUser(
                ip=run_input.deployment.node.ip,
                http_port=run_input.deployment.node.http_port,
                server_type=run_input.deployment.node.server_type
            )

            # Create module
            module = grpc_server_pb2.Module(
                id=run_input.deployment.module.get('id', ''),
                name=run_input.deployment.module.get('name', ''),
                description=run_input.deployment.module.get('description', ''),
                author=run_input.deployment.module.get('author', ''),
                module_url=run_input.deployment.module.get('module_url', ''),
                module_type=module_type,
                module_version=run_input.deployment.module.get('module_version', ''),
                module_entrypoint=run_input.deployment.module.get('module_entrypoint', '')
            )

            # Create config struct
            config_struct = struct_pb2.Struct()
            if run_input.deployment.config:
                if isinstance(run_input.deployment.config, dict):
                    config_struct.update(run_input.deployment.config)
                else:
                    config_struct.update(run_input.deployment.config.dict())

            # Create deployment based on module type
            deployment_classes = {
                "agent": grpc_server_pb2.AgentDeployment,
                "kb": grpc_server_pb2.BaseDeployment,
                "tool": grpc_server_pb2.ToolDeployment,
                "environment": grpc_server_pb2.BaseDeployment
            }
            
            DeploymentClass = deployment_classes[module_type]
            deployment = DeploymentClass(
                node_input=node_config,
                name=run_input.deployment.name,
                module=module,
                config=config_struct,
                initialized=False
            )

            # Create request with appropriate deployment field
            request_args = {
                "module_type": module_type,
                "consumer_id": run_input.consumer_id,
                "inputs": input_struct,
                f"{module_type}_deployment": deployment
            }
            
            request = grpc_server_pb2.ModuleRunRequest(**request_args)

            final_response = None
            async for response in stub.RunModule(request):
                final_response = response
                logger.info(f"Got response: {response}")

            output_types = {
                "agent": AgentRun,
                "kb": KBRun,
                "tool": ToolRun,
                "environment": EnvironmentRun
            }

            return output_types[module_type](
                consumer_id=run_input.consumer_id,
                inputs=run_input.inputs,
                deployment=run_input.deployment,
                orchestrator_runs=[],
                status=final_response.status,
                error=final_response.error,
                id=final_response.id,
                results=list(final_response.results),
                error_message=final_response.error_message,
                created_time=final_response.created_time,
                start_processing_time=final_response.start_processing_time,
                completed_time=final_response.completed_time,
                duration=final_response.duration
            )
    
    async def connect_ws(self, action: str):
        client_id = str(uuid.uuid4())
        full_url = f"{self.node_url}/ws/{action}/{client_id}"
        logger.info(f"Connecting to WebSocket: {full_url}")
        ws = await websockets.connect(full_url)
        self.connections[client_id] = ws
        self.current_client_id = client_id
        return client_id

    async def disconnect_ws(self, client_id: str):
        if client_id in self.connections:
            await self.connections[client_id].close()
            del self.connections[client_id]
        if self.current_client_id == client_id:
            self.current_client_id = None

    async def send_receive_ws(self, data, action: str):
        client_id = await self.connect_ws(action)
        
        try:
            if isinstance(data, AgentRunInput) or isinstance(data, OrchestratorRunInput):
                message = data.model_dump()
            else:
                message = data
            await self.connections[client_id].send(json.dumps(message))
            
            response = await self.connections[client_id].recv()
            return json.loads(response)
        finally:
            await self.disconnect_ws(client_id)

class UserClient:
    def __init__(self, node: NodeConfigUser):
        self.node = node
        self.node_url = node_to_url(node)
        self.connections = {}
        
        self.access_token = None
        logger.info(f"Node URL: {self.node_url}")

    async def create(self, module_type: str,
                     module_request: Union[AgentDeployment, EnvironmentDeployment, KBDeployment, OrchestratorDeployment, ToolDeployment]):
        """Generic method to create either an agent, orchestrator, environment, tool, kb or memory.

        Args:
            module_type: Either agent, orchestrator, environment, tool, kb or memory
            module_request: Either AgentDeployment, EnvironmentDeployment, OrchestratorDeployment, ToolDeployment, KBDeployment or MemoryDeployment
        """

        print(f"Creating {module_type}...")

        endpoint = f"{self.node_url}/{module_type}/create"
        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.access_token}',
                }
                response = await client.post(
                    endpoint,
                    json=module_request.model_dump(),
                    headers=headers
                )
                response.raise_for_status()

                # Convert response to appropriate return type
                return response.json()
        except HTTPStatusError as e:
            logger.info(f"HTTP error occurred: {e}")
            raise
        except RemoteProtocolError as e:
            error_msg = f"Run {module_type} failed to connect to the server at {self.node_url}. Please check if the server URL is correct and the server is running. Error details: {str(e)}"
            logger.error(error_msg)
            raise
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            raise

    async def _run_and_poll(self, run_input: Union[AgentRunInput, EnvironmentRunInput, OrchestratorRunInput, KBRunInput, ToolRunInput, Dict], module_type: str) -> Union[AgentRun, EnvironmentRun, OrchestratorRun, KBRun, ToolRun, Dict]:
        """Generic method to run and poll either an agent, orchestrator, environment, tool or KB.
        
        Args:
            run_input: Either AgentRunInput, OrchestratorRunInput, EnvironmentRunInput, KBRunInput, ToolRunInput or Dict
            module_type: Either 'agent', 'orchestrator', 'environment', 'tool' or 'kb'
        """
        print(f"Run input: {run_input}")
        print(f"Module type: {module_type}")
        # Start the run
        run = await getattr(self, f'run_{module_type}')(run_input)
        print(f"{module_type.title()} run started: {run}")

        current_results_len = 0
        while True:
            run = await getattr(self, f'check_{module_type}_run')(run)

            output = f"{run.status} {getattr(run, f'deployment').module['module_type']} {getattr(run, f'deployment').module['name']}"
            print(output)

            results = run.results
            status = run.status

            if len(results) > current_results_len:
                print("Output: ", results[-1])
                current_results_len += 1

            if status in ['completed', 'error']:
                break

            time.sleep(3)

        if status == 'completed':
            print(results)
        else:
            error_msg = run.error_message
            print(error_msg)
        return run

    async def run_agent_and_poll(self, agent_run_input: AgentRunInput) -> AgentRun:
        """Run an agent and poll for results until completion."""
        return await self._run_and_poll(agent_run_input, 'agent')

    async def run_tool_and_poll(self, tool_run_input: ToolRunInput) -> ToolRun:
        """Run a tool and poll for results until completion."""

        return await self._run_and_poll(tool_run_input, 'tool')

    async def run_orchestrator_and_poll(self, orchestrator_run_input: OrchestratorRunInput) -> OrchestratorRun:
        """Run an orchestrator and poll for results until completion."""
        return await self._run_and_poll(orchestrator_run_input, 'orchestrator')

    async def run_environment_and_poll(self, environment_input: EnvironmentRunInput) -> EnvironmentRun:
        """Run an environment and poll for results until completion."""
        return await self._run_and_poll(environment_input, 'environment')
    
    async def run_kb_and_poll(self, kb_input: KBDeployment) -> KBDeployment:
        """Run a knowledge base and poll for results until completion."""
        return await self._run_and_poll(kb_input, 'kb')

    async def check_user(self, user_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if a user exists on a node
        """
        endpoint = self.node_url + "/user/check"
        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                headers = {
                    'Content-Type': 'application/json', 
                }
                response = await client.post(
                    endpoint, 
                    json=user_input,
                    headers=headers
                )
                response.raise_for_status()
            return json.loads(response.text)
        except HTTPStatusError as e:
            logger.info(f"HTTP error occurred: {e}")
            raise  
        except RemoteProtocolError as e:
            error_msg = f"Check user failed to connect to the server at {self.node_url}. Please check if the server URL is correct and the server is running. Error details: {str(e)}"
            logger.info(error_msg)
            raise 
        except Exception as e:
            logger.info(f"An unexpected error occurred: {e}")
            raise

    async def register_user(self, user_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register a user on a node
        """
        endpoint = self.node_url + "/user/register"
        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                headers = {
                    'Content-Type': 'application/json', 
                }
                response = await client.post(
                    endpoint, 
                    json=user_input,
                    headers=headers
                )
                response.raise_for_status()
            return json.loads(response.text)
        except HTTPStatusError as e:
            logger.info(f"HTTP error occurred: {e}")
            raise  
        except RemoteProtocolError as e:
            error_msg = f"Register user failed to connect to the server at {self.node_url}. Please check if the server URL is correct and the server is running. Error details: {str(e)}"
            logger.error(error_msg)
            raise 
        except Exception as e:
            logger.info(f"An unexpected error occurred: {e}")
            raise

    async def _run_module(self, run_input: Union[AgentRunInput, OrchestratorRunInput, EnvironmentRunInput, ToolRunInput], module_type: str) -> Union[AgentRun, OrchestratorRun, EnvironmentRun, ToolRun]:
        """
        Generic method to run either an agent, orchestrator, environment, or tool on a node
        
        Args:
            run_input: Either AgentRunInput, OrchestratorRunInput, EnvironmentRunInput, or ToolRunInput
            module_type: Either 'agent', 'orchestrator', 'environment', or 'tool'
        """
        print(f"Running {module_type}...")
        print(f"Run input: {run_input}")
        print(f"Node URL: {self.node_url}")

        endpoint = f"{self.node_url}/{module_type}/run"
        
        # Convert dict to appropriate input type if needed
        input_class = {
            'agent': AgentRunInput,
            'orchestrator': OrchestratorRunInput,
            'environment': EnvironmentRunInput,
            'kb': KBRunInput,
            'tool': ToolRunInput
        }[module_type]
        
        if isinstance(run_input, dict):
            run_input = input_class(**run_input)

        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.access_token}',
                }
                response = await client.post(
                    endpoint,
                    json=run_input.model_dict(),
                    headers=headers
                )

                # Try to get error details even for error responses
                if response.status_code >= 400:
                    error_detail = response.json() if response.text else str(response)
                    logger.error(f"Server error response: {error_detail}")
                    raise Exception(f"Server returned error response: {error_detail}")
                    
                response.raise_for_status()
                
                # Convert response to appropriate return type
                return_class = {
                    'agent': AgentRun,
                    'orchestrator': OrchestratorRun,
                    'environment': EnvironmentRun,
                    'kb': KBRun,
                    'tool': ToolRun
                }[module_type]
                return return_class(**json.loads(response.text))
        except HTTPStatusError as e:
            logger.info(f"HTTP error occurred: {e}")
            raise
        except RemoteProtocolError as e:
            error_msg = f"Run {module_type} failed to connect to the server at {self.node_url}. Please check if the server URL is correct and the server is running. Error details: {str(e)}"
            logger.error(error_msg)
            raise
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            raise

    async def run_inference(self, inference_input: Union[ChatCompletionRequest, Dict]) -> ModelResponse:
        """
        Run inference on a node
        
        Args:
            inference_input: The inference input to run inference on
        """
        if isinstance(inference_input, dict):
            inference_input = ChatCompletionRequest(**inference_input)

        endpoint = f"{self.node_url}/inference/chat"

        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.access_token}',
                }
                response = await client.post(
                    endpoint,
                    json=inference_input.model_dump(),
                    headers=headers
                )
                print("Response: ", response.text)
                response.raise_for_status()
                return ModelResponse(**json.loads(response.text))
        except HTTPStatusError as e:
            logger.info(f"HTTP error occurred: {e}")
            raise
        except RemoteProtocolError as e:
            error_msg = f"Inference failed to connect to the server at {self.node_url}. Please check if the server URL is correct and the server is running. Error details: {str(e)}"
            logger.error(error_msg)
            raise
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            raise

    async def run_agent(self, agent_run_input: AgentRunInput) -> AgentRun:
        """Run an agent on a node"""
        return await self._run_module(agent_run_input, 'agent')

    async def run_tool(self, tool_run_input: ToolRunInput) -> ToolRun:
        """Run a tool on a node"""
        return await self._run_module(tool_run_input, 'tool')

    async def run_orchestrator(self, orchestrator_run_input: OrchestratorRunInput) -> OrchestratorRun:
        """Run an orchestrator on a node"""
        return await self._run_module(orchestrator_run_input, 'orchestrator')
    
    async def run_environment(self, environment_run_input: EnvironmentRunInput) -> EnvironmentRun:
        """Run an environment on a node"""
        return await self._run_module(environment_run_input, 'environment')

    async def run_kb(self, kb_run_input: KBRunInput) -> KBRun:
        """Run a knowledge base on a node"""
        return await self._run_module(kb_run_input, 'kb')

    async def check_run(
        self, 
        module_run: Union[AgentRun, OrchestratorRun, EnvironmentRun, KBRun, ToolRun], 
        module_type: str
    ) -> Union[AgentRun, OrchestratorRun, EnvironmentRun, KBRun, ToolRun]:
        """Generic method to check the status of a module run.
        
        Args:
            module_run: Either AgentRun, OrchestratorRun, EnvironmentRun, ToolRun or KBRun object
            module_type: Either 'agent', 'orchestrator', 'environment', 'tool' or 'kb'
        """
        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                response = await client.post(
                    f"{self.node_url}/{module_type}/check", 
                    json=module_run.model_dump()
                )
                response.raise_for_status()
            
            return_class = {
                'agent': AgentRun,
                'orchestrator': OrchestratorRun,
                'environment': EnvironmentRun,
                'kb': KBRun,
                'tool': ToolRun
            }[module_type]
            return return_class(**json.loads(response.text))
        except HTTPStatusError as e:
            logger.info(f"HTTP error occurred: {e}")
            raise  
        except Exception as e:
            logger.info(f"An unexpected error occurred: {e}")

    # Update existing methods to use the new generic one
    async def check_agent_run(self, agent_run: AgentRun) -> AgentRun:
        return await self.check_run(agent_run, 'agent')

    async def check_tool_run(self, tool_run: ToolRun) -> ToolRun:
        return await self.check_run(tool_run, 'tool')

    async def check_orchestrator_run(self, orchestrator_run: OrchestratorRun) -> OrchestratorRun:
        return await self.check_run(orchestrator_run, 'orchestrator')

    async def check_environment_run(self, environment_run: EnvironmentRun) -> EnvironmentRun:
        return await self.check_run(environment_run, 'environment')

    async def check_kb_run(self, kb_run: KBRun) -> KBRun:
        return await self.check_run(kb_run, 'kb')

    async def create_agent_run(self, agent_run_input: AgentRunInput) -> AgentRun:
        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                response = await client.post(
                    f"{self.node_url}/monitor/create_agent_run", json=agent_run_input.model_dump()
                )
                response.raise_for_status()
            return AgentRun(**json.loads(response.text))
        except HTTPStatusError as e:
            logger.info(f"HTTP error occurred: {e}")
            raise  
        except Exception as e:
            logger.info(f"An unexpected error occurred: {e}")
            logger.info(f"Full traceback: {traceback.format_exc()}")

    async def update_agent_run(self, agent_run: AgentRun):
        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                response = await client.post(
                    f"{self.node_url}/monitor/update_agent_run", json=agent_run.model_dump()
                )
                response.raise_for_status()
            return AgentRun(**json.loads(response.text))
        except HTTPStatusError as e:
            logger.info(f"HTTP error occurred: {e}")
            raise  
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            error_details = traceback.format_exc()
            print(f"Full traceback: {error_details}")

    async def read_storage(self, agent_run_id: str, output_dir: str, ipfs: bool = False) -> str:
        print("Reading from storage...")
        try:
            endpoint = f"{self.node_url}/{'storage/read_ipfs' if ipfs else 'storage/read'}/{agent_run_id}"

            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                response = await client.get(endpoint)
                response.raise_for_status()
                storage = response.content  
                print("Retrieved storage.")
            
                # Temporary file handling
                temp_file_name = None
                with tempfile.NamedTemporaryFile(delete=False, mode='wb') as tmp_file:
                    tmp_file.write(storage)  # storage is a bytes-like object
                    temp_file_name = tmp_file.name
        
                # Ensure output directory exists
                output_path = Path(output_dir)
                output_path.mkdir(parents=True, exist_ok=True)
        
                # Check if the file is a zip file and extract if true
                if zipfile.is_zipfile(temp_file_name):
                    with zipfile.ZipFile(temp_file_name, 'r') as zip_ref:
                        zip_ref.extractall(output_path)
                    print(f"Extracted storage to {output_dir}.")
                else:
                    shutil.copy(temp_file_name, output_path)
                    print(f"Copied storage to {output_dir}.")

                # Cleanup temporary file
                Path(temp_file_name).unlink(missing_ok=True)
        
                return output_dir         
        except HTTPStatusError as e:
            logger.info(f"HTTP error occurred: {e}")
            raise  
        except Exception as e:
            logger.info(f"An unexpected error occurred: {e}")
            logger.info(f"Full traceback: {traceback.format_exc()}")

    async def write_storage(self, storage_input: str, ipfs: bool = False, publish_to_ipns: bool = False, update_ipns_name: str = None) -> Dict[str, Any]:
        """Write storage to the node."""
        print("Writing storage")
        try:
            file = prepare_files(storage_input)
            endpoint = f"{self.node_url}/storage/write_ipfs" if ipfs else f"{self.node_url}/storage/write"
            
            if update_ipns_name:
                publish_to_ipns = True

            data = {
                "publish_to_ipns": publish_to_ipns,
                "update_ipns_name": update_ipns_name
            }
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                response = await client.post(
                    endpoint, 
                    files=file,
                    data=data,
                    timeout=600
                )
                response.raise_for_status()
                return response.json()
        except HTTPStatusError as e:
            logger.info(f"HTTP error occurred: {e}")
            raise  
        except Exception as e:
            logger.info(f"An unexpected error occurred: {e}")
            logger.info(f"Full traceback: {traceback.format_exc()}")
            return {}

    async def create_table(self, table_name: str, schema: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.post(
                f"{self.node_url}/local-db/create-table",
                json={"table_name": table_name, "schema": schema}
            )
            response.raise_for_status()
            return response.json()

    async def add_row(self, table_name: str, data: Dict[str, Any], schema: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.post(
                f"{self.node_url}/local-db/add-row",
                json={"table_name": table_name, "data": data, "schema": schema}
            )
            response.raise_for_status()
            return response.json()

    async def update_row(self, table_name: str, data: Dict[str, Any], condition: Dict[str, Any], schema: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.post(
                f"{self.node_url}/local-db/update-row",
                json={
                    "table_name": table_name,
                    "data": data,
                    "condition": condition,
                    "schema": schema
                }
            )
            response.raise_for_status()
            return response.json()

    async def delete_row(self, table_name: str, condition: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.post(
                f"{self.node_url}/local-db/delete-row",
                json={"table_name": table_name, "condition": condition}
            )
            response.raise_for_status()
            return response.json()

    async def list_tables(self) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.get(f"{self.node_url}/local-db/tables")
            response.raise_for_status()
            return response.json()

    async def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.get(f"{self.node_url}/local-db/table/{table_name}")
            response.raise_for_status()
            return response.json()

    async def query_table(self, table_name: str, columns: Optional[str] = None, condition: Optional[Union[str, Dict]] = None, order_by: Optional[str] = None, limit: Optional[int] = None) -> Dict[str, Any]:
        params = {"table_name": table_name}
        if columns:
            params["columns"] = columns
        if condition:
            params["condition"] = json.dumps(condition) if isinstance(condition, dict) else condition
        if order_by:
            params["order_by"] = order_by
        if limit:
            params["limit"] = limit

        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.get(
                f"{self.node_url}/local-db/table/{table_name}/rows",
                params=params
            )
            response.raise_for_status()
            return response.json()

    async def vector_search(
        self,
        table_name: str,
        vector_column: str,
        query_vector: List[float],
        columns: Optional[List[str]] = None,
        top_k: int = 5,
        include_similarity: bool = True
    ) -> Dict[str, Any]:
        """
        Perform a pgvector-based similarity search on a table's vector column.
        """
        payload = {
            "table_name": table_name,
            "vector_column": vector_column,
            "query_vector": query_vector,
            "columns": columns or ["text"],
            "top_k": top_k,
            "include_similarity": include_similarity,
        }
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.post(
                f"{self.node_url}/local-db/vector_search",
                json=payload
            )
            response.raise_for_status()
            return response.json()


def zip_directory(file_path, zip_path):
    """Utility function to zip the content of a directory while preserving the folder structure."""
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(file_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, start=os.path.abspath(file_path).split(os.sep)[0])
                zipf.write(file_path, arcname)

def prepare_files(file_path: str) -> List[Tuple[str, str]]:
    """Prepare files for upload."""
    if os.path.isdir(file_path):
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmpfile:
            zip_directory(file_path, tmpfile.name)
            tmpfile.close()  
            file = {'file': open(tmpfile.name, 'rb')}
    else:
        file = {'file': open(file_path, 'rb')}
    
    return file

