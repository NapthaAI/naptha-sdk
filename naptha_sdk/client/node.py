from copy import deepcopy
from google.protobuf.json_format import MessageToDict
import grpc
import httpx
import asyncio
from httpx import HTTPStatusError, RemoteProtocolError
import json
import random
import time
import traceback
from typing import Dict, Any, Union, List
import uuid
import websockets
from google.protobuf import struct_pb2

from naptha_sdk.client import grpc_server_pb2
from naptha_sdk.client import grpc_server_pb2_grpc
from naptha_sdk.schemas import AgentRun, AgentRunInput, EnvironmentRun, EnvironmentRunInput, OrchestratorRun, \
    OrchestratorRunInput, AgentDeployment, EnvironmentDeployment, OrchestratorDeployment, KBDeployment, KBRunInput, \
    KBRun, MemoryDeployment, MemoryRunInput, MemoryRun, ToolRunInput, ToolRun, NodeConfig, NodeConfigUser, ToolDeployment, SecretInput
from naptha_sdk.utils import get_logger, node_to_url
from naptha_sdk.client.grpc_pool_manager import get_grpc_pool_instance

logger = get_logger(__name__)
HTTP_TIMEOUT = 300

class NodeClient:
    def __init__(self, node: NodeConfig):
        self.node = node
        self.node_communication_protocol = node.node_communication_protocol
        self.node_url = self.node_to_url(node)
        self.connections = {}
        self.access_token = None
        
        # Initialize pool for gRPC clients
        if self.node_communication_protocol == 'grpc':
            self._init_grpc_pool()
            
        logger.info(f"Node URL: {self.node_url}")
        
    def _init_grpc_pool(self):
        """Initialize the connection pool with optimized settings"""
        # These settings are optimized for high concurrency (10k agents)
        self.pool = get_grpc_pool_instance(
            max_channels=500,  # Increased for extreme concurrency
            buffer_size=100,   # Larger buffer to reuse connections
            channel_options=[
                ("grpc.max_send_message_length", 10 * 1024 * 1024),        # 10MB
                ("grpc.max_receive_message_length", 10 * 1024 * 1024),     # 10MB
                ("grpc.keepalive_time_ms", 30000),                         # 30 seconds
                ("grpc.keepalive_timeout_ms", 10000),                      # 10 seconds
                ("grpc.keepalive_permit_without_calls", 1),                # Allow keepalives when idle
                ("grpc.http2.max_pings_without_data", 5),                  # Allow pings without data
                ("grpc.http2.min_time_between_pings_ms", 10000),           # 10 seconds minimum
                ("grpc.max_connection_idle_ms", 300000),                   # 5 minutes idle timeout
                ("grpc.max_connection_age_ms", 600000),                    # 10 minutes max age
                ("grpc.max_connection_age_grace_ms", 5000),                # 5 seconds grace period
                ("grpc.enable_retries", 1),                                # Enable retries
                ("grpc.service_config", '{"methodConfig": [{"name":[{}], "retryPolicy":{"maxAttempts":5,"initialBackoff":"0.1s","maxBackoff":"10s","backoffMultiplier":2,"retryableStatusCodes":["UNAVAILABLE"]}}]}')
            ]
        )
        # Start pool monitoring in background to track connection stats
        asyncio.create_task(self.pool.monitor_pool(interval=60))

    def node_to_url(self, node: NodeConfig):
        ports = node.ports
        if len(ports) == 0:
            raise ValueError("No ports found for node")
        if node.node_communication_protocol == 'ws':
            return f"ws://{node.ip}:{random.choice(ports)}"
        elif node.node_communication_protocol == 'wss':
            return f"wss://{node.ip}"
        elif node.node_communication_protocol == 'grpc':
            return f"{node.ip}:{random.choice(ports)}"
        else:
            raise ValueError("Invalid node communication protocol. Node communication protocol must be either 'ws' or 'grpc'.")

    async def check_user(self, user_input: Dict[str, str]) -> Dict[str, Any]:
        if self.node.node_communication_protocol == 'ws':
            return await self.check_user_ws(user_input)
        elif self.node.node_communication_protocol == 'grpc':
            return await self.check_user_grpc(user_input)
        else:
            raise ValueError("Invalid node communication protocol. Node communication protocol must be either 'ws' or 'grpc'.")

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
        if self.node.node_communication_protocol == 'ws':
            return await self.register_user_ws(user_input)
        elif self.node.node_communication_protocol == 'grpc':
            return await self.register_user_grpc(user_input)
        else:
            raise ValueError("Invalid node communication protocol. Node communication protocol must be either 'ws' or 'grpc'.")
        
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

    async def run_module(self, module_type: str, run_input: Union[AgentRunInput, KBRunInput, ToolRunInput, MemoryRunInput, EnvironmentRunInput]):
        if self.node.node_communication_protocol in ['ws', 'wss']:
            return await self.run_module_ws(module_type, run_input)
        elif self.node.node_communication_protocol == 'grpc':
            NUM_RETRIES = 5  # Increased from 3
            backoff_base = 2
            backoff_cap = 60  # Cap at 60 seconds
            jitter_factor = 0.2  # Add 20% jitter
            
            for attempt in range(NUM_RETRIES):
                try:
                    return await self.run_module_grpc(module_type, run_input)
                    
                except grpc.aio.AioRpcError as e:
                    # Log every error to help with debugging
                    logger.error(f"gRPC error on attempt {attempt+1}/{NUM_RETRIES}: {e.code()}: {e.details()}")
                    
                    # These status codes are potential candidates for retry
                    retriable_status_codes = [
                        grpc.StatusCode.CANCELLED,
                        grpc.StatusCode.UNAVAILABLE,
                        grpc.StatusCode.DEADLINE_EXCEEDED,
                        grpc.StatusCode.RESOURCE_EXHAUSTED
                    ]
                    
                    if e.code() in retriable_status_codes and attempt < NUM_RETRIES - 1:
                        # Calculate backoff time with jitter
                        backoff_time = min(backoff_base ** attempt, backoff_cap)
                        jitter = backoff_time * jitter_factor * (random.random() * 2 - 1)
                        final_backoff = max(1, backoff_time + jitter)
                        
                        logger.info(f"Retriable gRPC error. Retrying in {final_backoff:.2f}s (attempt {attempt+1}/{NUM_RETRIES})")
                        await asyncio.sleep(final_backoff)
                        continue
                    
                    # Not retriable or out of retries
                    logger.error(f"gRPC call failed permanently: {e}")
                    raise
                    
                except Exception as e:
                    logger.error(f"Unexpected error during gRPC call: {str(e)}")
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    raise
                    
            raise Exception(f"Failed to run module after {NUM_RETRIES} attempts")
        else:
            raise ValueError("Invalid node communication protocol. Node communication protocol must be either 'ws', 'wss', or 'grpc'.")

    
    async def run_module_ws(self, module_type: str, run_input: Union[AgentRunInput, KBRunInput, ToolRunInput, MemoryRunInput, EnvironmentRunInput]):
        run_input_dict = deepcopy(run_input)
        run_input_dict = run_input_dict.model_dict()
        response = await self.send_receive_ws(run_input_dict, f"{module_type}/run")
        
        output_types = {
            "agent": AgentRun,
            "tool": ToolRun,
            "kb": KBRun,
            "memory": MemoryRun,
            "orchestrator": OrchestratorRun,
            "environment": EnvironmentRun,
        }
        
        if response['status'] == 'success':
            return output_types[module_type](**response['data'])
        else:
            logger.error(f"Error running {module_type}: {response['message']}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            raise Exception(response['message'])

    async def run_module_grpc(self, module_type: str, run_input):
        # Use the connection pool context manager
        async with self.pool.channel_context(self.node_url) as channel:
            try:
                stub = grpc_server_pb2_grpc.GrpcServerStub(channel)
                
                # Convert inputs to a Struct
                input_struct = struct_pb2.Struct()
                if run_input.inputs:
                    input_data = (
                        run_input.inputs.dict() if hasattr(run_input.inputs, "dict") else run_input.inputs
                    )
                    input_struct.update(input_data)

                # Use NodeConfigInput from the proto
                node_config = grpc_server_pb2.NodeConfigInput(
                    ip=run_input.deployment.node.ip,
                    user_communication_port=run_input.deployment.node.user_communication_port,
                    user_communication_protocol=run_input.deployment.node.user_communication_protocol,
                )

                # Create the module proto message
                module = grpc_server_pb2.Module(
                    id=run_input.deployment.module.get("id", ""),
                    name=run_input.deployment.module.get("name", ""),
                    description=run_input.deployment.module.get("description", ""),
                    author=run_input.deployment.module.get("author", ""),
                    module_url=run_input.deployment.module.get("module_url", ""),
                    module_type=module_type,
                    module_version=run_input.deployment.module.get("module_version", ""),
                    module_entrypoint=run_input.deployment.module.get("module_entrypoint", ""),
                    execution_type=run_input.deployment.module.get("execution_type", ""),
                )

                # Create config struct for deployment
                config_struct = struct_pb2.Struct()
                if run_input.deployment.config:
                    config_data = (
                        run_input.deployment.config.dict()
                        if hasattr(run_input.deployment.config, "dict")
                        else run_input.deployment.config
                    )
                    config_struct.update(config_data)

                # Map module types to the appropriate deployment proto message
                deployment_classes = {
                    "agent": grpc_server_pb2.AgentDeployment,
                    "kb": grpc_server_pb2.BaseDeployment,
                    "tool": grpc_server_pb2.ToolDeployment,
                    "environment": grpc_server_pb2.BaseDeployment,
                    "memory": grpc_server_pb2.BaseDeployment,
                }
                DeploymentClass = deployment_classes.get(module_type)
                if not DeploymentClass:
                    raise ValueError(f"Unsupported module type: {module_type}")
                    
                deployment = DeploymentClass(
                    node_input=node_config,
                    name=run_input.deployment.name,
                    module=module,
                    config=config_struct,
                    initialized=False,
                )

                # Build the request
                request_args = {
                    "module_type": module_type,
                    "consumer_id": run_input.consumer_id,
                    "inputs": input_struct,
                    f"{module_type}_deployment": deployment,
                }
                
                # Add signature if it exists in the input
                if hasattr(run_input, "signature") and run_input.signature:
                    request_args["signature"] = run_input.signature
                    
                request = grpc_server_pb2.ModuleRunRequest(**request_args)

                # Call the service with a timeout
                timeout = 1800  # 30 minutes
                
                # Track progress
                start_time = time.time()
                response_count = 0
                final_response = None
                
                try:
                    async for response in stub.RunModule(request, timeout=timeout):
                        response_count += 1
                        final_response = response
                        
                        # Log progress for long-running operations
                        if response_count % 5 == 0:
                            elapsed = time.time() - start_time
                            logger.info(f"Module run in progress: {elapsed:.2f}s elapsed, {response_count} updates received")
                            
                except asyncio.CancelledError:
                    logger.warning(f"Module run was cancelled for {module_type}")
                    raise
                
                # Return the appropriate output type
                output_types = {
                    "agent": AgentRun,
                    "kb": KBRun,
                    "tool": ToolRun,
                    "environment": EnvironmentRun,
                    "memory": MemoryRun,
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
                    error_message=final_response.error_message if hasattr(final_response, "error_message") else None,
                    created_time=final_response.created_time if hasattr(final_response, "created_time") else None,
                    start_processing_time=final_response.start_processing_time if hasattr(final_response, "start_processing_time") else None,
                    completed_time=final_response.completed_time if hasattr(final_response, "completed_time") else None,
                    duration=final_response.duration if hasattr(final_response, "duration") else None,
                    signature=getattr(final_response, "signature", None),
                )
                
            except grpc.aio.AioRpcError:
                # Let the run_module method handle retries
                raise
                
            except Exception as e:
                logger.error(f"Unexpected error in run_module_grpc: {str(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                raise
    
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

    async def _run_and_poll(self, run_input: Union[AgentRunInput, EnvironmentRunInput, OrchestratorRunInput, KBRunInput, ToolRunInput, Dict], module_type: str, secrets: List[SecretInput] = []) -> Union[AgentRun, EnvironmentRun, OrchestratorRun, KBRun, ToolRun, Dict]:
        """Generic method to run and poll either an agent, orchestrator, environment, tool or KB.
        
        Args:
            run_input: Either AgentRunInput, OrchestratorRunInput, EnvironmentRunInput, KBRunInput, ToolRunInput or Dict
            module_type: Either 'agent', 'orchestrator', 'environment', 'tool' or 'kb'
        """
        print(f"Run input: {run_input}")
        print(f"Module type: {module_type}")
        # Start the run
        run = await getattr(self, f'run_{module_type}')(run_input, secrets)
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

    async def run_agent_and_poll(self, agent_run_input: AgentRunInput, secrets: List[SecretInput] = []) -> AgentRun:
        """Run an agent module and poll for results until completion."""
        return await self._run_and_poll(agent_run_input, 'agent', secrets)

    async def run_tool_and_poll(self, tool_run_input: ToolRunInput, secrets: List[SecretInput] = []) -> ToolRun:
        """Run a tool module and poll for results until completion."""
        return await self._run_and_poll(tool_run_input, 'tool', secrets)

    async def run_orchestrator_and_poll(self, orchestrator_run_input: OrchestratorRunInput, secrets: List[SecretInput] = []) -> OrchestratorRun:
        """Run an orchestrator module and poll for results until completion."""
        return await self._run_and_poll(orchestrator_run_input, 'orchestrator', secrets)

    async def run_environment_and_poll(self, environment_input: EnvironmentRunInput, secrets: List[SecretInput] = []) -> EnvironmentRun:
        """Run an environment module and poll for results until completion."""
        return await self._run_and_poll(environment_input, 'environment', secrets)
    
    async def run_kb_and_poll(self, kb_input: KBDeployment, secrets: List[SecretInput] = []) -> KBDeployment:
        """Run a knowledge base module and poll for results until completion."""
        return await self._run_and_poll(kb_input, 'kb', secrets)

    async def run_memory_and_poll(self, memory_input: MemoryDeployment, secrets: List[SecretInput] = []) -> MemoryDeployment:
        """Run a memory module and poll for results until completion."""
        return await self._run_and_poll(memory_input, 'memory', secrets)

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

    async def _run_module(self, run_input: Union[AgentRunInput, OrchestratorRunInput, EnvironmentRunInput, ToolRunInput], module_type: str, secrets: List[SecretInput] = []) -> Union[AgentRun, OrchestratorRun, EnvironmentRun, ToolRun]:
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
            'memory': MemoryRunInput,
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
                    json={
                        f"{module_type}_run_input": run_input.model_dict(),
                        "secrets": [SecretInput(**secret).model_dict() for secret in secrets]
                    },
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
                    'memory': MemoryRun,
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

    async def run_agent(self, agent_run_input: AgentRunInput, secrets: List[SecretInput] = []) -> AgentRun:
        """Run an agent module on a node"""
        return await self._run_module(agent_run_input, 'agent', secrets)

    async def run_tool(self, tool_run_input: ToolRunInput, secrets: List[SecretInput] = []) -> ToolRun:
        """Run a tool module on a node"""
        return await self._run_module(tool_run_input, 'tool', secrets)

    async def run_orchestrator(self, orchestrator_run_input: OrchestratorRunInput, secrets: List[SecretInput] = []) -> OrchestratorRun:
        """Run an orchestrator module on a node"""
        return await self._run_module(orchestrator_run_input, 'orchestrator', secrets)
    
    async def run_environment(self, environment_run_input: EnvironmentRunInput, secrets: List[SecretInput] = []) -> EnvironmentRun:
        """Run an environment module on a node"""
        return await self._run_module(environment_run_input, 'environment', secrets)

    async def run_kb(self, kb_run_input: KBRunInput, secrets: List[SecretInput] = []) -> KBRun:
        """Run a knowledge base module on a node"""
        return await self._run_module(kb_run_input, 'kb', secrets)

    async def run_memory(self, memory_run_input: MemoryRunInput, secrets: List[SecretInput] = []) -> MemoryRun:
        """Run a memory module on a node"""
        return await self._run_module(memory_run_input, 'memory', secrets)

    async def check_run(
        self, 
        module_run: Union[AgentRun, OrchestratorRun, EnvironmentRun, KBRun, MemoryRun, ToolRun], 
        module_type: str
    ) -> Union[AgentRun, OrchestratorRun, EnvironmentRun, KBRun, MemoryRun, ToolRun]:
        """Generic method to check the status of a module run.
        
        Args:
            module_run: Either AgentRun, OrchestratorRun, EnvironmentRun, ToolRun, KBRun or MemoryRun object
            module_type: Either 'agent', 'orchestrator', 'environment', 'tool', 'kb' or 'memory'
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
                'memory': MemoryRun,
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

    async def check_memory_run(self, memory_run: MemoryRun) -> MemoryRun:
        return await self.check_run(memory_run, 'memory')
    
    async def _send_request(self, method: str, endpoint: str, data: dict = {}, params: dict = {}) -> str:
        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                headers = {
                    'Content-Type': 'application/json',
                }

                if method == "GET":
                    response = await client.get(endpoint, headers=headers)
                elif method == "POST":
                    response = await client.post(endpoint, json=data, headers=headers, params=params)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                response.raise_for_status()

                return response.json()
        except HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e}")
            raise
        except Exception as e:
            logger.error(f"An error occurred: {e}")
            raise

