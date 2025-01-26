import argparse
import asyncio
from dotenv import load_dotenv
import os
import shlex
from rich.console import Console
from rich.table import Table
from rich import box
import json
import yaml
import httpx

from naptha_sdk.client.hub import user_setup_flow
from naptha_sdk.client.naptha import Naptha
from naptha_sdk.schemas import AgentDeployment, ChatCompletionRequest, EnvironmentDeployment, \
    OrchestratorDeployment, OrchestratorRunInput, EnvironmentRunInput, KBDeployment, KBRunInput, MemoryDeployment, MemoryRunInput, ToolDeployment, ToolRunInput, NodeConfigUser
from naptha_sdk.storage.storage_client import StorageClient
from naptha_sdk.storage.schemas import (
    CreateStorageRequest, DeleteStorageRequest, ListStorageRequest, 
    ReadStorageRequest, UpdateStorageRequest, SearchStorageRequest, StorageType
)
from naptha_sdk.user import get_public_key, sign_consumer_id
from naptha_sdk.utils import url_to_node, get_env_data, get_logger
from naptha_sdk.secrets import create_secret
from httpx import HTTPStatusError

load_dotenv(override=True)
logger = get_logger(__name__)

HTTP_TIMEOUT = 300

async def list_nodes(naptha):
    nodes = await naptha.hub.list_nodes()
    
    if not nodes:
        console = Console()
        console.print("[red]No nodes found.[/red]")
        return

    console = Console()
    table = Table(
        box=box.ROUNDED,
        show_lines=True,
        title="Available Nodes",
        title_style="bold cyan",
        header_style="bold blue",
        row_styles=["", "dim"]  # Alternating row styles
    )

    # Get dynamic headers from first node
    headers = list(nodes[0].keys())

    def format_models(models):
        if isinstance(models, str):
            models = eval(models)  # Safely convert string representation to list
        return '\n'.join(models)  # One model per line


    # Define columns with specific formatting
    table.add_column("Node ID", justify="left")
    table.add_column("Node IP", justify="left")
    table.add_column("Node Owner", justify="left")
    table.add_column("OS", justify="left")
    table.add_column("Arch", justify="left")
    table.add_column("User \nComm \nProtocol", justify="left")
    table.add_column("User \nComm \nPort", justify="left")
    table.add_column("# Node\nComm \nServers", justify="left")
    table.add_column("Node \nComm \nProtocol", justify="left")
    table.add_column("Available \nModels", justify="left", no_wrap=True)
    table.add_column("# \nGPUs", justify="left")
    table.add_column("Provider \nTypes", justify="left")

    # Add rows
    for node in nodes:
        table.add_row(
            node['id'],
            node['ip'],
            node['owner'],
            node['os'],
            node['arch'],
            node['user_communication_protocol'],
            str(node['user_communication_port']),
            str(node['num_node_communication_servers']),
            node['node_communication_protocol'],
            format_models(node['models']), 
            str(node['num_gpus']),
            str(node['provider_types']) 
        )
    # Print table and summary
    console.print()
    console.print(table)
    console.print(f"\n[green]Total nodes:[/green] {len(nodes)}")

async def list_modules(naptha, module_type=None, module_name=None):
    """List modules of a specific type or all modules if no type specified.
    
    Args:
        naptha: Naptha client instance
        module_type (str, optional): Type of module to list (agent, tool, etc.)
        module_name (str, optional): Specific module name to filter by
    """
    # Get modules of specified type or all modules
    modules = await naptha.hub.list_modules(module_type=module_type)
    
    if not modules:
        console = Console()
        console.print(f"[red]No {module_type or 'modules'} found.[/red]")
        return

    # Configure table
    title = f"Available {module_type.title() if module_type else 'Modules'}"
    console = Console()
    table = Table(
        box=box.ROUNDED,
        show_lines=True,
        title=title,
        title_style="bold cyan",
        header_style="bold blue",
        row_styles=["", "dim"]
    )

    # Define columns with consistent formatting
    columns = {
        "Name": {"justify": "left", "style": "green"},
        "ID": {"justify": "left"},
        "Author": {"justify": "left"},
        "Description": {"justify": "left", "max_width": 50},
        "Parameters": {"justify": "left", "max_width": 40},
        "Module URL": {"justify": "left", "no_wrap": True},  # Removed max_width to show full URL
        "Module Version": {"justify": "left"},
        "Module Type": {"justify": "left"},
        "Module Entrypoint": {"justify": "left"}
    }

    # Add columns to table
    for col_name, col_props in columns.items():
        table.add_column(col_name, **col_props)

    # Add rows
    for module in modules:
        # Make URL clickable with link styling
        url = f"[link={module['module_url']}]{module['module_url']}[/link]"
        
        table.add_row(
            module['name'],
            module['id'],
            module['author'],
            module['description'],
            str(module['parameters']),
            url,  # Using formatted URL with link
            module['module_version'],
            module.get('module_type', ''),
            module.get('module_entrypoint', '')
        )

    # Print table and summary
    console.print()
    console.print(table)
    console.print(f"\n[green]Total {module_type} modules:[/green] {len(modules)}")

async def list_servers(naptha):
    servers = await naptha.hub.list_servers()
    print(servers)
    if not servers:
        console = Console()
        console.print("[red]No servers found.[/red]")
        return

    console = Console()
    table = Table(
        box=box.ROUNDED,
        show_lines=True,
        title="Available Servers",
        title_style="bold cyan",
        header_style="bold blue",
        row_styles=["", "dim"]  # Alternating row styles
    )

    # Add columns
    table.add_column("ID", justify="left")
    table.add_column("Node ID", justify="left", max_width=30)
    table.add_column("Communication Protocol", justify="left")
    table.add_column("Port", justify="left")

    # Add rows
    for server in servers:
        table.add_row(
            server['id'],
            server['node_id'],
            server['communication_protocol'],
            str(server['port'])
        )

    # Print table and summary
    console.print()
    console.print(table)
    console.print(f"\n[green]Total servers:[/green] {len(servers)}")

async def create(
        naptha,
        module_name,
        agent_modules: list = None,
        agent_nodes: list = None,
        tool_modules: list = None,
        tool_nodes: list = None,
        kb_modules: list = None,
        kb_nodes: list = None,
        memory_modules: list = None,
        memory_nodes: list = None,
        environment_modules: list = None,
        environment_nodes: list = None
):
    module_type = module_name.split(":")[0] if ":" in module_name else "agent"
    module_name = module_name.split(":")[-1]  # Remove prefix if exists

    user = await naptha.node.check_user(user_input={"public_key": naptha.hub.public_key})

    if user['is_registered']:
        print("Found user...", user)
    else:
        print("No user found. Registering user...")
        user = await naptha.node.register_user(user_input=user)
        print(f"User registered: {user}.")

    # Create auxiliary deployments if needed
    aux_deployments = {
        "agent_deployments": [
            AgentDeployment(
                name=agent_module,
                module={"name": agent_module},
                node=NodeConfigUser(ip=agent_node.strip())
            ) for agent_module, agent_node in zip(agent_modules or [], agent_nodes or [])
        ],
        "tool_deployments": [
            ToolDeployment(
                name=tool_module,
                module={"name": tool_module},
                node=NodeConfigUser(ip=tool_node.strip())
            ) for tool_module, tool_node in zip(tool_modules or [], tool_nodes or [])
        ],
        "kb_deployments": [
            KBDeployment(
                name=kb_module,
                module={"name": kb_module},
                node=NodeConfigUser(ip=kb_node.strip())
            ) for kb_module, kb_node in zip(kb_modules or [], kb_nodes or [])
        ],
        "memory_deployments": [
            MemoryDeployment(
                name=memory_module,
                module={"name": memory_module},
                node=NodeConfigUser(ip=memory_node.strip())
            ) for memory_module, memory_node in zip(memory_modules or [], memory_nodes or [])
        ],
        "environment_deployments": [
            EnvironmentDeployment(
                name=env_module,
                module={"name": env_module},
                node=NodeConfigUser(ip=env_node.strip())
            ) for env_module, env_node in zip(environment_modules or [], environment_nodes or [])
        ],
    }

    # Define deployment configurations for each module type
    deployment_configs = {
        "agent": lambda: AgentDeployment(
            name=module_name,
            module={"name": module_name},
            node=url_to_node(os.getenv("NODE_URL")),
        ),
        "tool": lambda: ToolDeployment(
            name=module_name,
            module={"name": module_name},
            node=url_to_node(os.getenv("NODE_URL"))
        ),
        "orchestrator": lambda: OrchestratorDeployment(
            name=module_name,
            module={"name": module_name},
            node=url_to_node(os.getenv("NODE_URL")),
            **aux_deployments
        ),
        "environment": lambda: EnvironmentDeployment(
            name=module_name,
            module={"name": module_name},
            node=url_to_node(os.getenv("NODE_URL"))
        ),
        "kb": lambda: KBDeployment(
            name=module_name,
            module={"name": module_name},
            node=url_to_node(os.getenv("NODE_URL"))
        ),
        "memory": lambda: MemoryDeployment(
            name=module_name,
            module={"name": module_name},
            node=url_to_node(os.getenv("NODE_URL"))
        )
    }

    # Get deployment configuration for module type
    if module_type not in deployment_configs:
        raise ValueError(f"Unsupported module type: {module_type}")

    deployment = deployment_configs[module_type]()
    result = await naptha.node.create(module_type, deployment)
    print(f"{module_type.title()} creation result: {result}")


async def run(
    naptha,
    module_name,
    parameters=None, 
    agent_nodes=None,
    tool_nodes=None,
    environment_nodes=None,
    kb_nodes=None,
    memory_nodes=None,
    config=None
):   

    module_type = module_name.split(":")[0] if ":" in module_name else "agent" # Default to agent for backwards compatibility

    user = await naptha.node.check_user(user_input={"public_key": naptha.hub.public_key})

    if user['is_registered'] == True:
        print("Found user...", user)
    else:
        print("No user found. Registering user...")
        user = await naptha.node.register_user(user_input=user)
        print(f"User registered: {user}.")

    # Handle sub-deployments
    agent_deployments = []
    if agent_nodes:
        for agent_node in agent_nodes:
            agent_deployments.append(AgentDeployment(node=NodeConfigUser(ip=agent_node.strip())))
    tool_deployments = []
    if tool_nodes:
        for tool_node in tool_nodes:
            tool_deployments.append(ToolDeployment(node=NodeConfigUser(ip=tool_node.strip())))
    environment_deployments = []
    if environment_nodes:
        for environment_node in environment_nodes:
            environment_deployments.append(EnvironmentDeployment(node=NodeConfigUser(ip=environment_node.strip())))
    kb_deployments = []
    if kb_nodes:
        for kb_node in kb_nodes:
            kb_deployments.append(KBDeployment(node=NodeConfigUser(ip=kb_node.strip())))
    memory_deployments = []
    if memory_nodes:
        for memory_node in memory_nodes:
            memory_deployments.append(MemoryDeployment(node=NodeConfigUser(ip=memory_node.strip())))


    if module_type == "agent":
        print("Running Agent...")

        agent_deployment = AgentDeployment(
            module={"id": module_name, "name": module_name.split(":")[-1], "module_type": module_type}, 
            node=url_to_node(os.getenv("NODE_URL")), 
            config=config,
            tool_deployments=tool_deployments,
            kb_deployments=kb_deployments,
            memory_deployments=memory_deployments,
            environment_deployments=environment_deployments
        )

        agent_run_input = {
            'consumer_id': user['id'],
            "inputs": parameters,
            "deployment": agent_deployment.model_dump(),
            "signature": sign_consumer_id(user['id'], os.getenv("PRIVATE_KEY"))
        }
        print(f"Agent run input: {agent_run_input}")

        agent_run = await naptha.node.run_agent_and_poll(agent_run_input)

    elif module_type == "tool":
        print("Running Tool...")
        tool_deployment = ToolDeployment(
            module={"id": module_name, "name": module_name.split(":")[-1], "module_type": module_type},
            node=url_to_node(os.getenv("NODE_URL")),
            config=config
        )

        tool_run_input = ToolRunInput(
            consumer_id=user['id'],
            inputs=parameters,
            deployment=tool_deployment,
            signature=sign_consumer_id(user['id'], os.getenv("PRIVATE_KEY"))
        )
        tool_run = await naptha.node.run_tool_and_poll(tool_run_input)

    elif module_type == "orchestrator":
        print("Running Orchestrator...")

        orchestrator_deployment = OrchestratorDeployment(
            module={"id": module_name, "name": module_name.split(":")[-1], "module_type": module_type}, 
            node=url_to_node(os.getenv("NODE_URL")),
            agent_deployments=agent_deployments,
            environment_deployments=environment_deployments,
            kb_deployments=kb_deployments,
            memory_deployments=memory_deployments,
            config=config
        )

        orchestrator_run_input = OrchestratorRunInput(
            consumer_id=user['id'],
            inputs=parameters,
            deployment=orchestrator_deployment,
            signature=sign_consumer_id(user['id'], os.getenv("PRIVATE_KEY"))
        )
        orchestrator_run = await naptha.node.run_orchestrator_and_poll(orchestrator_run_input)

    elif module_type == "environment":
        print("Running Environment...")

        environment_deployment = EnvironmentDeployment(
            module={"id": module_name, "name": module_name.split(":")[-1], "module_type": module_type}, 
            node=url_to_node(os.getenv("NODE_URL")),
            config=config
        )

        environment_run_input = EnvironmentRunInput(
            inputs=parameters,
            deployment=environment_deployment,
            consumer_id=user['id'],
            signature=sign_consumer_id(user['id'], os.getenv("PRIVATE_KEY"))
        )
        environment_run = await naptha.node.run_environment_and_poll(environment_run_input)

    elif module_type == "kb":
        print("Running Knowledge Base...")

        kb_deployment = KBDeployment(
            module={"id": module_name, "name": module_name.split(":")[-1], "module_type": module_type}, 
            node=url_to_node(os.getenv("NODE_URL")),
            config=config
        )

        kb_run_input = KBRunInput(
            consumer_id=user['id'],
            inputs=parameters,
            deployment=kb_deployment,
            signature=sign_consumer_id(user['id'], os.getenv("PRIVATE_KEY"))
        )
        kb_run = await naptha.node.run_kb_and_poll(kb_run_input)
    elif module_type == "memory":
        print("Running Memory Module...")

        memory_deployment = MemoryDeployment(
            module={"id": module_name, "name": module_name.split(":")[-1], "module_type": module_type}, 
            node=url_to_node(os.getenv("NODE_URL")),
            config=config
        )

        memory_run_input = MemoryRunInput(
            consumer_id=user['id'],
            inputs=parameters,
            deployment=memory_deployment,
            signature=sign_consumer_id(user['id'], os.getenv("PRIVATE_KEY"))
        )
        memory_run = await naptha.node.run_memory_and_poll(memory_run_input)     
    else:
        print(f"Module type {module_type} not supported.")

async def storage_interaction(naptha, storage_type, operation, path, data=None, schema=None, options=None, file=None):
    """Handle storage interactions using StorageClient"""
    storage_client = StorageClient(naptha.node.node)
    print(f"Storage interaction: {storage_type}, {operation}, {path}, {data}, {schema}, {options}, {file}")

    try:
        # Convert string storage type to enum
        storage_type = StorageType(storage_type)

        # Special handling for filesystem/IPFS file operations
        if storage_type in [StorageType.FILESYSTEM, StorageType.IPFS]:
            if operation == "create" and file:
                with open(file, 'rb') as f:
                    request = CreateStorageRequest(
                        storage_type=storage_type,
                        path=path,
                        file=f,
                        options=json.loads(options) if options else {}
                    )
                    result = await storage_client.execute(request)
                    print(f"Create {storage_type} result: {result}")
                    return result
                    
            elif operation == "read":
                request = ReadStorageRequest(
                    storage_type=storage_type,
                    path=path,
                    options=json.loads(options) if options else {}
                )
                result = await storage_client.execute(request)
                print(f"Read {storage_type} result: {result}")
                # Handle downloaded file
                if isinstance(result.data, bytes):
                    output_dir = "./downloads"
                    os.makedirs(output_dir, exist_ok=True)
                    output_path = os.path.join(output_dir, os.path.basename(path))
                    with open(output_path, 'wb') as f:
                        f.write(result.data)
                    print(f"File downloaded to: {output_path}")
                return result

        # Handle database and other operations
        match operation:
            case "create":
                if schema:
                    request = CreateStorageRequest(
                        storage_type=storage_type,
                        path=path,
                        data=json.loads(schema)
                    )
                elif data:
                    request = CreateStorageRequest(
                        storage_type=storage_type,
                        path=path,
                        data=json.loads(data)
                    )
                else:
                    raise ValueError("Either schema or data must be provided for create command")
                    
            case "read":
                request = ReadStorageRequest(
                    storage_type=storage_type,
                    path=path,
                    options=json.loads(options) if options else {}
                )
                
            case "update":
                if not data:
                    raise ValueError("Data must be provided for update command")
                request = UpdateStorageRequest(
                    storage_type=storage_type,
                    path=path,
                    data=json.loads(data),
                    options=json.loads(options) if options else {}
                )
                
            case "delete":
                request = DeleteStorageRequest(
                    storage_type=storage_type,
                    path=path,
                    options=json.loads(options) if options else {}
                )
                
            case "list":
                request = ListStorageRequest(
                    storage_type=storage_type,
                    path=path,
                    options=json.loads(options) if options else {}
                )
                
            case "search":
                if not data:
                    raise ValueError("Query data must be provided for search command")
                request = SearchStorageRequest(
                    storage_type=storage_type,
                    path=path,
                    query=json.loads(data),
                    options=json.loads(options) if options else {}
                )

        result = await storage_client.execute(request)
        print(f"{operation} {storage_type} result: {result}")
        return result

    except Exception as e:
        print(f"Storage operation failed: {str(e)}")
        raise

def _parse_list_arg(args, arg_name, default=None, split_char=','):
    """Helper function to parse list arguments with common logic."""
    if hasattr(args, arg_name) and getattr(args, arg_name) is not None:
        value = getattr(args, arg_name)
        return value.split(split_char) if split_char in value else [value]
    return default

def _parse_json_or_str_arg(arg_value):
    """Helper function to parse a string that could be JSON or key=value format."""
    if arg_value is None:
        return None
        
    try:
        return json.loads(arg_value)
    except json.JSONDecodeError:
        params = shlex.split(arg_value)
        parsed_params = {}
        for param in params:
            key, value = param.split('=')
            # Try to parse value as JSON if it looks like a dict
            try:
                if value.startswith('{') and value.endswith('}'):
                    value = json.loads(value)
            except json.JSONDecodeError:
                pass
            parsed_params[key] = value
        return parsed_params

def _parse_str_args(args):
    # Parse all list arguments
    args.agent_nodes = _parse_list_arg(args, 'agent_nodes', default=None)
    args.tool_nodes = _parse_list_arg(args, 'tool_nodes', default=None)
    args.environment_nodes = _parse_list_arg(args, 'environment_nodes', default=None)
    args.kb_nodes = _parse_list_arg(args, 'kb_nodes', default=None)
    args.memory_nodes = _parse_list_arg(args, 'memory_nodes', default=None)
    args.agent_modules = _parse_list_arg(args, 'agent_modules', default=None)
    args.tool_modules = _parse_list_arg(args, 'tool_modules', default=None)
    args.kb_modules = _parse_list_arg(args, 'kb_modules', default=None)
    args.memory_modules = _parse_list_arg(args, 'memory_modules', default=None)
    args.environment_modules = _parse_list_arg(args, 'environment_modules', default=None)
    
    # Parse parameters and config using the same function
    if hasattr(args, 'parameters') and args.parameters:
        args.parameters = _parse_json_or_str_arg(args.parameters)
        print("Parsed parameters:", args.parameters)
    if hasattr(args, 'config') and args.config:
        args.config = _parse_json_or_str_arg(args.config)
        print("Parsed config:", args.config)
        
    return args

async def _send_request(method: str, endpoint: str, data: dict = {}, params: dict = {}) -> str:
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
        print(f"HTTP error occurred: {e}")
        raise
    except Exception as e:
        print(f"An error occurred: {e}")
        raise

async def get_server_public_key() -> str:
    endpoint = f"{os.getenv('NODE_URL')}/public_key"
    return await _send_request("GET", endpoint)

def _parse_metadata_args(args, module_type):
    """Parse metadata arguments and return a module configuration dictionary.
    
    Args:
        args: The command line arguments
        module_type: The type of module (agent, orchestrator, etc.)
        
    Returns:
        dict: Module configuration dictionary
    """
    metadata = None
    if hasattr(args, 'create') and args.create is not None:
        metadata = args.create
    elif hasattr(args, 'update') and args.update is not None:
        metadata = args.update
        
    if metadata is None:
        return None
        
    params = shlex.split(metadata)
    parsed_params = {}
    for param in params:
        key, value = param.split('=')
        parsed_params[key] = value

    # Only check required metadata if this is a new module creation
    if hasattr(args, 'create') and args.create is not None:
        required_metadata = ['description', 'parameters', 'module_url']
        missing_metadata = [param for param in required_metadata if param not in parsed_params]
        if missing_metadata:
            print(f"Missing required metadata: {', '.join(missing_metadata)}")
            return None
        
        module_config = {
            "id": f"{module_type}:{args.module_name}",
            "name": args.module_name,
            "description": parsed_params['description'],
            "parameters": parsed_params['parameters'],
            "author": f"user:{args.public_key}",
            "module_url": parsed_params['module_url'],
            "module_type": parsed_params.get('module_type', module_type),
            "module_version": parsed_params.get('module_version', 'v0.1'),
            "module_entrypoint": parsed_params.get('module_entrypoint', 'run.py'),
            "execution_type": parsed_params.get('execution_type', 'package')
        }
    else:
        module_config = {
            "id": f"{module_type}:{args.module_name}",
            **parsed_params
        }

    return module_config

async def main():
    public_key = get_public_key(os.getenv("PRIVATE_KEY")) if os.getenv("PRIVATE_KEY") else None
    hub_username = os.getenv("HUB_USERNAME")
    hub_password = os.getenv("HUB_PASSWORD")
    hub_url = os.getenv("HUB_URL")

    naptha = Naptha()

    parser = argparse.ArgumentParser(description="CLI with for Naptha")
    subparsers = parser.add_subparsers(title="commands", dest="command")

    # Node parser
    nodes_parser = subparsers.add_parser("nodes", help="List available nodes.")
    nodes_parser.add_argument("-s", '--list_servers', action='store_true', help='List servers')

    # Agent parser
    agents_parser = subparsers.add_parser("agents", help="List available agents.")
    agents_parser.add_argument('module_name', nargs='?', help='Optional agent name')
    agents_parser.add_argument("-c", '--create', type=str, help='Metadata in "key=value" format')
    agents_parser.add_argument("-u", '--update', type=str, help='Metadata in "key=value" format')
    agents_parser.add_argument('-d', '--delete', action='store_true', help='Delete a agent')

    # Orchestrator parser
    orchestrators_parser = subparsers.add_parser("orchestrators", help="List available orchestrators.")
    orchestrators_parser.add_argument('module_name', nargs='?', help='Optional orchestrator name')
    orchestrators_parser.add_argument("-c", '--create', type=str, help='Metadata in "key=value" format')
    orchestrators_parser.add_argument("-u", '--update', type=str, help='Metadata in "key=value" format')
    orchestrators_parser.add_argument('-d', '--delete', action='store_true', help='Delete an orchestrator')

    # Environment parser
    environments_parser = subparsers.add_parser("environments", help="List available environments.")
    environments_parser.add_argument('module_name', nargs='?', help='Optional environment name')
    environments_parser.add_argument("-c", '--create', type=str, help='Metadata in "key=value" format')
    environments_parser.add_argument("-u", '--update', type=str, help='Metadata in "key=value" format')
    environments_parser.add_argument('-d', '--delete', action='store_true', help='Delete an environment')

    # Persona parser
    personas_parser = subparsers.add_parser("personas", help="List available personas.")
    personas_parser.add_argument('module_name', nargs='?', help='Optional persona name')
    personas_parser.add_argument("-c", '--create', type=str, help='Metadata in "key=value" format')
    personas_parser.add_argument("-u", '--update', type=str, help='Metadata in "key=value" format')
    personas_parser.add_argument('-d', '--delete', action='store_true', help='Delete a persona')

    # Tool parser
    tools_parser = subparsers.add_parser("tools", help="List available tools.")
    tools_parser.add_argument('module_name', nargs='?', help='Optional tool name')
    tools_parser.add_argument("-c", '--create', type=str, help='Metadata in "key=value" format')
    tools_parser.add_argument("-u", '--update', type=str, help='Metadata in "key=value" format')
    tools_parser.add_argument('-d', '--delete', action='store_true', help='Delete a tool')

    # Memory parser
    memories_parser = subparsers.add_parser("memories", help="List available memories.")
    memories_parser.add_argument('module_name', nargs='?', help='Optional memory name')
    memories_parser.add_argument("-c", '--create', type=str, help='Metadata in "key=value" format')
    memories_parser.add_argument("-u", '--update', type=str, help='Metadata in "key=value" format')
    memories_parser.add_argument('-d', '--delete', action='store_true', help='Delete a memory')
    memories_parser.add_argument('-m', '--memory_nodes', type=str, help='Memory nodes', default=["http://localhost:7001"])

    # Knowledge base parser
    kbs_parser = subparsers.add_parser("kbs", help="List available knowledge bases.")
    kbs_parser.add_argument('module_name', nargs='?', help='Optional knowledge base name')
    kbs_parser.add_argument("-c", '--create', type=str, help='Metadata in "key=value" format')
    kbs_parser.add_argument("-u", '--update', type=str, help='Metadata in "key=value" format')
    kbs_parser.add_argument('-d', '--delete', action='store_true', help='Delete a knowledge base')
    kbs_parser.add_argument('-k', '--kb_nodes', type=str, help='Knowledge base nodes')

    # Create parser
    create_parser = subparsers.add_parser("create", help="Execute create command.")
    create_parser.add_argument("module", help="Select the module to create")
    create_parser.add_argument("-am", "--agent_modules", help="Agent modules to create")
    create_parser.add_argument("-an", "--agent_nodes", help="Agent nodes to take part in orchestrator runs.")
    create_parser.add_argument("-tm", "--tool_modules", help="Tool modules to create")
    create_parser.add_argument("-tn", "--tool_nodes", help="Tool nodes to take part in module runs.")
    create_parser.add_argument("-km", "--kb_modules", help="Knowledge base modules to create")
    create_parser.add_argument("-kn", "--kb_nodes", help="Knowledge base nodes to take part in module runs.")
    create_parser.add_argument("-mm", "--memory_modules", help="Memory modules to create")
    create_parser.add_argument("-mn", "--memory_nodes", help="Memory nodes to take part in module runs.")
    create_parser.add_argument("-em", "--environment_modules", help="Environment module to create")
    create_parser.add_argument("-en", "--environment_nodes", help="Environment nodes to store data during agent runs.")

    # Run parser
    run_parser = subparsers.add_parser("run", help="Execute run command.")
    run_parser.add_argument("agent", help="Select the agent to run")
    run_parser.add_argument("-p", '--parameters', type=str, help='Parameters in "key=value" format')
    run_parser.add_argument("-n", "--agent_nodes", help="Agent nodes to take part in module runs.")
    run_parser.add_argument("-t", "--tool_nodes", help="Tool nodes to take part in module runs.")
    run_parser.add_argument("-e", "--environment_nodes", help="Environment nodes to store data during module runs.")
    run_parser.add_argument('-k', '--kb_nodes', type=str, help='Knowledge base nodes to take part in module runs.')
    run_parser.add_argument('-m', '--memory_nodes', type=str, help='Memory nodes')
    run_parser.add_argument("-c", "--config", type=str, help='Config in "key=value" format')

    # Inference parser
    inference_parser = subparsers.add_parser("inference", help="Run model inference.")
    inference_subparser = inference_parser.add_subparsers(dest="inference_command", help="Inference operations")
    
    # Completions command
    completions_parser = inference_subparser.add_parser("completions", help="Generate completions")
    completions_parser.add_argument("prompt", help="Input prompt for the model")
    completions_parser.add_argument("-m", "--model", help="Model to use for inference", default="phi3:mini")
    completions_parser.add_argument("-p", "--parameters", type=str, help='Additional model parameters in "key=value" format')

    # Models command
    models_parser = inference_subparser.add_parser("models", help="List available models")

    # Storage parser
    storage_parser = subparsers.add_parser("storage", help="Interact with Node storage.")
    storage_parser.add_argument("storage_type", help="The type of storage", choices=["db", "fs", "ipfs"])
    storage_parser.add_argument("operation", help="The operation to run", choices=["create", "read", "update", "delete", "list", "search"])
    storage_parser.add_argument("path", help="The path to store the object")
    storage_parser.add_argument("-d", "--data", help="Data to write to storage")
    storage_parser.add_argument("-s", "--schema", help="Schema to write to storage")
    storage_parser.add_argument("-o", "--options", help="Options to use with storage")
    storage_parser.add_argument("-f", "--file", help="File path for fs/ipfs operations")
    storage_parser.add_argument("--output", help="Output path for downloaded files", default="./downloads")

    # Signup command
    signup_parser = subparsers.add_parser("signup", help="Sign up a new user.")

    # Publish command
    publish_parser = subparsers.add_parser("publish", help="Publish agents.")
    publish_parser.add_argument("-d", "--decorator", help="Publish module via decorator", action="store_true")
    publish_parser.add_argument("-r", "--register", 
                              help="Register modules with hub. Optionally provide a GitHub URL to skip IPFS storage", 
                              nargs='?', 
                              const=True,
                              metavar="URL")
    publish_parser.add_argument("-s", "--subdeployments", help="Publish subdeployments", action="store_true")

    # Add API Key Command
    deploy_secrets_parser = subparsers.add_parser("deploy-secrets", help="Add API keys or tokens.")
    deploy_secrets_parser.add_argument("-e", "--env", help="Add API key from environment variable. Provide the key name.", action="store_true")
    deploy_secrets_parser.add_argument("-o", "--override", help="Override API key in DB with env file values.", action="store_true")
    
    # TODO: Implement remove-key functionality
    # deploy_secrets_parser.add_argument("-r", "--remove-key", help="Specify the key name to remove from DB.")

        
    async with naptha as naptha:
        args = parser.parse_args()
        args = _parse_str_args(args)
        args.public_key = naptha.hub.public_key
        if args.command == "signup":
            _, _ = await user_setup_flow(hub_url, public_key)
        elif args.command in [
            "nodes", "agents", "orchestrators", "environments", 
            "personas", "kbs", "memories", "tools", "run", "inference", 
            "publish", "create", "storage", "deploy-secrets"
        ]:
            if not naptha.hub.is_authenticated:
                if not hub_username or not hub_password:
                    print(
                        "Please set HUB_USERNAME and HUB_PASSWORD environment variables or sign up first (run naptha signup).")
                    return
                success, _, _ = await naptha.hub.signin(hub_username, hub_password)
                if not success:
                    print("Authentication failed. Please check your username and password.")
                    return

            if args.command == "nodes":
                if not args.list_servers:
                    await list_nodes(naptha)   
                else:
                    await list_servers(naptha)
            elif args.command == "agents":
                if not args.module_name:
                    await list_modules(naptha, module_type='agent')
                elif args.update and len(args.module_name.split()) == 1:
                    module_config = _parse_metadata_args(args, "agent")
                    if module_config:
                        await naptha.hub.update_module("agent", module_config)
                elif args.delete and len(args.module_name.split()) == 1:
                    await naptha.hub.delete_module("agent", args.module_name)
                elif len(args.module_name.split()) == 1:
                    module_config = _parse_metadata_args(args, "agent")
                    if module_config:
                        await naptha.hub.create_module("agent", module_config)
                else:
                    print("Invalid command.")
            elif args.command == "orchestrators":
                if not args.module_name:
                    await list_modules(naptha, module_type='orchestrator')
                elif args.update and len(args.module_name.split()) == 1:
                    module_config = _parse_metadata_args(args, "orchestrator")
                    if module_config:
                        await naptha.hub.update_module("orchestrator", module_config)
                elif args.delete and len(args.module_name.split()) == 1:
                    await naptha.hub.delete_module("orchestrator", args.module_name)
                elif len(args.module_name.split()) == 1:
                    module_config = _parse_metadata_args(args, "orchestrator")
                    if module_config:
                        await naptha.hub.create_module("orchestrator", module_config)
                else:
                    print("Invalid command.")
            elif args.command == "environments":
                if not args.module_name:
                    await list_modules(naptha, module_type='environment')
                elif args.update and len(args.module_name.split()) == 1:
                    module_config = _parse_metadata_args(args, "environment")
                    if module_config:
                        await naptha.hub.update_module("environment", module_config)
                elif args.delete and len(args.module_name.split()) == 1:
                    await naptha.hub.delete_module("environment", args.module_name)
                elif len(args.module_name.split()) == 1:
                    module_config = _parse_metadata_args(args, "environment")
                    if module_config:
                        await naptha.hub.create_module("environment", module_config)
                else:
                    print("Invalid command.")
            elif args.command == "tools":
                if not args.module_name:
                    await list_modules(naptha, module_type='tool')
                elif args.update and len(args.module_name.split()) == 1:
                    module_config = _parse_metadata_args(args, "tool")
                    if module_config:
                        await naptha.hub.update_module("tool", module_config)
                elif args.delete and len(args.module_name.split()) == 1:
                    await naptha.hub.delete_module("tool", args.module_name)
                elif len(args.module_name.split()) == 1:
                    module_config = _parse_metadata_args(args, "tool")
                    if module_config:
                        await naptha.hub.create_module("tool", module_config)
                else:
                    print("Invalid command.")
            elif args.command == "personas":
                if not args.module_name:
                    await list_modules(naptha, module_type='persona')
                elif args.update and len(args.module_name.split()) == 1:
                    module_config = _parse_metadata_args(args, "persona")
                    if module_config:
                        await naptha.hub.update_module("persona", module_config)
                elif args.delete and len(args.module_name.split()) == 1:
                    await naptha.hub.delete_module("persona", args.module_name)
                elif len(args.module_name.split()) == 1:
                    module_config = _parse_metadata_args(args, "persona")
                    if module_config:
                        await naptha.hub.create_module("persona", module_config)
                else:
                    print("Invalid command.")
            elif args.command == "memories":
                if not args.module_name:
                    await list_modules(naptha, module_type='memory')
                elif args.update and len(args.module_name.split()) == 1:
                    module_config = _parse_metadata_args(args, "memory")
                    if module_config:
                        await naptha.hub.update_module("memory", module_config)
                elif args.delete and len(args.module_name.split()) == 1:
                    await naptha.hub.delete_module("memory", args.module_name)
                elif len(args.module_name.split()) == 1:
                    module_config = _parse_metadata_args(args, "memory")
                    if module_config:
                        await naptha.hub.create_module("memory", module_config)
                else:
                    await list_modules(naptha, module_type='memory')
            elif args.command == "kbs":
                if not args.module_name:
                    await list_modules(naptha, module_type='kb')
                elif args.update and len(args.module_name.split()) == 1:
                    module_config = _parse_metadata_args(args, "kb")
                    if module_config:
                        await naptha.hub.update_module("kb", module_config)
                elif args.delete and len(args.module_name.split()) == 1:
                    await naptha.hub.delete_module("kb", args.module_name)
                elif len(args.module_name.split()) == 1:
                    module_config = _parse_metadata_args(args, "kb")
                    if module_config:
                        await naptha.hub.create_module("kb", module_config)
                else:
                    await list_modules(naptha, module_type='kb')
            elif args.command == "create":
                await create(naptha, args.module, args.agent_modules, args.agent_nodes, args.tool_modules, args.tool_nodes, args.kb_modules, args.kb_nodes, args.memory_modules, args.memory_nodes, args.environment_modules, args.environment_nodes)
            elif args.command == "run":                    
                await run(naptha, args.agent, args.parameters, args.agent_nodes, args.tool_nodes, args.environment_nodes, args.kb_nodes, args.memory_nodes, args.config)
            elif args.command == "inference":
                if args.inference_command == "models":
                    response = await naptha.inference_client.list_models()
                    print("Response: ", response)
                else:
                    request = ChatCompletionRequest(
                        messages=[{"role": "user", "content": args.prompt}],
                        model=args.model,
                    )
                    await naptha.inference_client.run_inference(request)
            elif args.command == "storage":
                await storage_interaction(
                    naptha, 
                    args.storage_type, 
                    args.operation, 
                    args.path, 
                    data=args.data, 
                    schema=args.schema, 
                    options=args.options, 
                    file=args.file
                )
            elif args.command == "publish":
                await naptha.publish_modules(args.decorator, args.register, args.subdeployments)
            elif args.command == "deploy-secrets":
                if args.env:
                    response = await get_server_public_key()
                    encrypted_data = create_secret(get_env_data(), naptha.hub.user_id, response["public_key"])
                else:
                    response = await get_server_public_key()
                    key_name = input("Enter the key name: ").strip()
                    key_value = input(f"Enter the value for {key_name}: ").strip()
                    
                    if not key_name or not key_value:
                        logger.error("Both key name and key value are required.")
                        return
                    
                    data_dict = {key_name: key_value}
                    encrypted_data = create_secret(data_dict, naptha.hub.user_id, response["public_key"])

                result = await _send_request(
                    "POST",
                    f"{os.getenv('NODE_URL')}/user/secret/create",
                    encrypted_data,
                    { "is_update": args.override }
                )

                logger.info(result)
                
        else:
            parser.print_help()

def cli():
    import sys
    import traceback
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}")
        print(f"Full traceback: {traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    cli()