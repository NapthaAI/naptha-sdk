import argparse
import asyncio
from dotenv import load_dotenv
from naptha_sdk.client.naptha import Naptha
from naptha_sdk.client.hub import user_setup_flow
from naptha_sdk.user import get_public_key
from naptha_sdk.schemas import AgentDeployment, EnvironmentDeployment, OrchestratorDeployment, OrchestratorRunInput, EnvironmentRunInput, NodeConfigUser
import os
import shlex
from rich.console import Console
from rich.table import Table
from rich import box
import json
import yaml
from dotenv import load_dotenv

from naptha_sdk.client.hub import user_setup_flow
from naptha_sdk.client.naptha import Naptha
from naptha_sdk.schemas import AgentDeployment, ChatCompletionRequest, EnvironmentDeployment, \
    OrchestratorDeployment, OrchestratorRunInput, EnvironmentRunInput, KBDeployment, KBRunInput, ToolDeployment, ToolRunInput
from naptha_sdk.storage.storage_provider import StorageProvider
from naptha_sdk.storage.schemas import (
    CreateStorageRequest, DeleteStorageRequest, ListStorageRequest, 
    ReadStorageRequest, UpdateStorageRequest, SearchStorageRequest,StorageType, 
)
from naptha_sdk.user import get_public_key, sign_consumer_id
from naptha_sdk.utils import url_to_node

load_dotenv(override=True)

def load_yaml_to_dict(file_path):
    with open(file_path, 'r') as file:
        # Load the YAML content into a Python dictionary
        yaml_content = yaml.safe_load(file)
    return yaml_content

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

    # Define columns with specific formatting
    table.add_column("ID", justify="left")
    table.add_column("IP", justify="left")
    table.add_column("Owner", justify="left")
    table.add_column("OS", justify="left")
    table.add_column("Arch", justify="left")
    table.add_column("Num Servers", justify="left")
    table.add_column("Server Type", justify="left")
    table.add_column("HTTP Port", justify="left")
    table.add_column("Models", justify="left")
    table.add_column("Num GPUs", justify="left")
    table.add_column("Provider Types", justify="left")

    # Add rows
    for node in nodes:
        table.add_row(
            node['id'],
            node['ip'],
            node['owner'],
            node['os'],
            node['arch'],
            str(node['num_servers']),
            node['server_type'],
            str(node['http_port']),
            str(node['models']), 
            str(node['num_gpus']),
            str(node['provider_types']) 
        )
    # Print table and summary
    console.print()
    console.print(table)
    console.print(f"\n[green]Total nodes:[/green] {len(nodes)}")

async def list_agents(naptha):
    agents = await naptha.hub.list_agents()
    
    if not agents:
        console = Console()
        console.print("[red]No agents found.[/red]")
        return

    console = Console()
    table = Table(
        box=box.ROUNDED,
        show_lines=True,
        title="Available Agents",
        title_style="bold cyan",
        header_style="bold blue",
        row_styles=["", "dim"]  # Alternating row styles
    )

    # Define columns with specific formatting
    table.add_column("Name", justify="left", style="green")
    table.add_column("ID", justify="left")
    table.add_column("Author", justify="left")
    table.add_column("Description", justify="left", max_width=50)
    table.add_column("Parameters", justify="left", max_width=30)
    table.add_column("Module URL", justify="left", max_width=30)
    table.add_column("Module Version", justify="center")

    # Add rows
    for agent in agents:
        table.add_row(
            agent['name'],
            agent['id'],
            agent['author'],
            agent['description'],
            str(agent['parameters']),
            agent['module_url'],
            agent['module_version'],
        )

    # Print table and summary
    console.print()
    console.print(table)
    console.print(f"\n[green]Total agents:[/green] {len(agents)}")

async def list_tools(naptha):
    tools = await naptha.hub.list_tools()
    
    if not tools:
        console = Console()
        console.print("[red]No tools found.[/red]")
        return

    console = Console()
    table = Table(
        box=box.ROUNDED,
        show_lines=True,
        title="Available Tools", 
        title_style="bold cyan",
        header_style="bold blue",
        row_styles=["", "dim"]  # Alternating row styles
    )

    # Define columns with specific formatting
    table.add_column("Name", justify="left", style="green")
    table.add_column("ID", justify="left")
    table.add_column("Author", justify="left")
    table.add_column("Description", justify="left", max_width=50)
    table.add_column("Parameters", justify="left", max_width=30)
    table.add_column("Module URL", justify="left", max_width=30)
    table.add_column("Module Version", justify="center")

    # Add rows
    for tool in tools:
        table.add_row(
            tool['name'],
            tool['id'],
            tool['author'],
            tool['description'],
            str(tool['parameters']),
            tool['module_url'],
            tool['module_version'],
        )

    # Print table and summary
    console.print()
    console.print(table)
    console.print(f"\n[green]Total tools:[/green] {len(tools)}")

async def list_orchestrators(naptha):
    orchestrators = await naptha.hub.list_orchestrators()
    
    if not orchestrators:
        console = Console()
        console.print("[red]No orchestrators found.[/red]")
        return

    console = Console()
    table = Table(
        box=box.ROUNDED,
        show_lines=True,
        title="Available Orchestrators",
        title_style="bold cyan",
        header_style="bold blue",
        row_styles=["", "dim"]  # Alternating row styles
    )

    # Define columns with specific formatting
    table.add_column("Name", justify="left", style="green")
    table.add_column("ID", justify="left")
    table.add_column("Author", justify="left")
    table.add_column("Description", justify="left", max_width=50)
    table.add_column("Parameters", justify="left", max_width=30)
    table.add_column("Module URL", justify="left", max_width=30)
    table.add_column("Module Version", justify="center")

    # Add rows
    for orchestrator in orchestrators:
        table.add_row(
            orchestrator['name'],
            orchestrator['id'],
            orchestrator['author'],
            orchestrator['description'],
            str(orchestrator['parameters']),
            orchestrator['module_url'],
            orchestrator['module_version'],
        )

    # Print table and summary
    console.print()
    console.print(table)
    console.print(f"\n[green]Total orchestrators:[/green] {len(orchestrators)}")

async def list_environments(naptha):
    environments = await naptha.hub.list_environments()
    
    if not environments:
        console = Console()
        console.print("[red]No environments found.[/red]")
        return

    console = Console()
    table = Table(
        box=box.ROUNDED,
        show_lines=True,
        title="Available Environments",
        title_style="bold cyan",
        header_style="bold blue",
        row_styles=["", "dim"]  # Alternating row styles
    )

    # Define columns with specific formatting
    table.add_column("Name", justify="left", style="green")
    table.add_column("ID", justify="left")
    table.add_column("Author", justify="left")
    table.add_column("Description", justify="left", max_width=50)
    table.add_column("Parameters", justify="left", max_width=30)
    table.add_column("Module URL", justify="left", max_width=30)
    table.add_column("Module Version", justify="center")

    # Add rows
    for environment in environments:
        table.add_row(
            environment['name'],
            environment['id'],
            environment['author'],
            environment['description'],
            str(environment['parameters']),
            environment['module_url'],
            environment['module_version'],
        )

    # Print table and summary
    console.print()
    console.print(table)
    console.print(f"\n[green]Total environments:[/green] {len(environments)}")

async def list_personas(naptha):
    personas = await naptha.hub.list_personas()
    
    if not personas:
        console = Console()
        console.print("[red]No personas found.[/red]")
        return

    console = Console()
    table = Table(
        box=box.ROUNDED,
        show_lines=True,
        title="Available Personas",
        title_style="bold cyan",
        header_style="bold blue",
        row_styles=["", "dim"]  # Alternating row styles
    )

    # Define columns with specific formatting
    table.add_column("Name", justify="left", style="green")
    table.add_column("ID", justify="left")
    table.add_column("Author", justify="left")
    table.add_column("Description", justify="left", max_width=50)
    table.add_column("Parameters", justify="left", max_width=30)
    table.add_column("Module URL", justify="left", max_width=40)
    table.add_column("Module Version", justify="center")
    table.add_column("Module Entrypoint", justify="center")

    # Add rows
    for persona in personas:
        table.add_row(
            persona['name'],
            persona['id'],
            persona['author'],
            persona['description'],
            persona['parameters'],
            persona['module_url'],
            persona['module_version'],
            persona['module_entrypoint']
        )

    # Print table and summary
    console.print()
    console.print(table)
    console.print(f"\n[green]Total personas:[/green] {len(personas)}")

async def list_memories(naptha, memory_name=None):
    memories = await naptha.hub.list_memories(memory_name=memory_name)

    if not memories:
        console = Console()
        console.print("[red]No memories found.[/red]")
        return
    
    console = Console()
    table = Table(
        box=box.ROUNDED,
        show_lines=True,
        title="Available memories",
        title_style="bold cyan",
        header_style="bold blue",
        row_styles=["", "dim"]
    )

    table.add_column("Name", justify="left", style="green")
    table.add_column("ID", justify="left")
    table.add_column("Author", justify="left")
    table.add_column("Description", justify="left", max_width=50)
    table.add_column("Parameters", justify="left", max_width=40)
    table.add_column("Module URL", justify="left", max_width=40)
    table.add_column("Module Version", justify="center")

    # Add rows
    for memory in memories:
        table.add_row(
            memory['name'],
            memory['id'],
            memory['author'],
            memory['description'],
            memory['parameters'],
            memory['module_url'],
            memory['module_version']
        )

    # Print table and summary
    console.print()
    console.print(table)
    console.print(f"\n[green]Total memories:[/green] {len(memories)}")

async def list_memory_content(naptha, memory_name):
    rows = await naptha.node.query_table(
        table_name=memory_name,   
        columns="*",
        condition=None,
        order_by=None,
        limit=None
    )
    
    if not rows.get('rows'):
        console = Console()
        console.print("[red]No content found in memory.[/red]")
        return

    console = Console()
    table = Table(
        box=box.ROUNDED,
        show_lines=True,
        title=f"Memory Content: {memory_name}",
        title_style="bold cyan",
        header_style="bold blue",
        row_styles=["", "dim"]
    )

    # Add headers
    headers = list(rows['rows'][0].keys())
    for header in headers:
        if header.lower() in ['id', 'module_url']:
            table.add_column(header, justify="left", max_width=40)
        elif header.lower() in ['title', 'name']:
            table.add_column(header, justify="left", style="green", max_width=40)
        elif header.lower() in ['text', 'description', 'content']:
            table.add_column(header, justify="left", max_width=60)
        else:
            table.add_column(header, justify="left", max_width=30)

    # Add rows
    for row in rows['rows']:
        table.add_row(*[str(row.get(key, '')) for key in headers])

    # Print table and summary
    console.print()
    console.print(table)
    console.print(f"\n[green]Total rows:[/green] {len(rows['rows'])}")

async def add_data_to_memory(naptha, memory_name, data, user_id=None, memory_node_url="http://localhost:7001"):
    try:
        # Parse the data string into a dictionary
        data_dict = {}
        # Split by spaces, but keep quoted strings together
        parts = shlex.split(data)
        
        for part in parts:
            if '=' in part:
                key, value = part.split('=', 1)
                # Remove quotes if they exist
                value = value.strip("'\"")
                data_dict[key] = value

        data_dict = [data_dict]
        
        memory_run_input = {
            "consumer_id": user_id,
            "inputs": {
                "mode": "add_data",
                "data": json.dumps(data_dict)
            },
            "memory_deployment": {
                "name": memory_name,
                "module": {
                    "name": memory_name
                },
                "memory_node_url": memory_node_url
            }
        }

        memory_run = await naptha.node.run_memory_and_poll(memory_run_input)
        console = Console()
        console.print(f"\n[green]Successfully added data to memory:[/green] {memory_name}")
        console.print(memory_run)
        
    except Exception as e:
        console = Console()
        console.print(f"\n[red]Error adding data to memory:[/red] {str(e)}")
                  
async def list_kbs(naptha, kb_name=None):
    kbs = await naptha.hub.list_kbs(kb_name=kb_name)
    
    if not kbs:
        console = Console()
        console.print("[red]No knowledge bases found.[/red]")
        return

    console = Console()
    table = Table(
        box=box.ROUNDED,
        show_lines=True,
        title="Available Knowledge Bases",
        title_style="bold cyan", 
        header_style="bold blue",
        row_styles=["", "dim"]  # Alternating row styles
    )

    # Define columns with specific formatting
    table.add_column("Name", justify="left", style="green")
    table.add_column("ID", justify="left")
    table.add_column("Author", justify="left")
    table.add_column("Description", justify="left", max_width=50)
    table.add_column("Parameters", justify="left", max_width=40)
    table.add_column("Module URL", justify="left", max_width=40)
    table.add_column("Module Type", justify="left")
    table.add_column("Module Version", justify="center")

    # Add rows
    for kb in kbs:
        table.add_row(
            kb['name'],
            kb['id'],
            kb['author'],
            kb['description'],
            kb['parameters'],
            kb['module_url'],
            kb['module_type'],
            kb['module_version']
        )

    # Print table and summary
    console.print()
    console.print(table)
    console.print(f"\n[green]Total knowledge bases:[/green] {len(kbs)}")

async def list_servers(naptha):
    servers = await naptha.hub.list_servers()
    
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
    table.add_column("Name", justify="left", style="green")
    table.add_column("ID", justify="left")
    table.add_column("Connection", justify="left")
    table.add_column("Node ID", justify="left", max_width=30)

    # Add rows
    for server in servers:
        table.add_row(
            server['name'],
            server['id'],
            server['connection_string'],
            server['node_id'][:30] + "..."  # Truncate long node ID
        )

    # Print table and summary
    console.print()
    console.print(table)
    console.print(f"\n[green]Total servers:[/green] {len(servers)}")

async def create_agent(naptha, agent_config):
    print(f"Agent Config: {agent_config}")
    agent = await naptha.hub.create_agent(agent_config)
    if isinstance(agent, dict):
        print(f"Agent created: {agent}")
    elif isinstance(agent, list):
        print(f"Agent created: {agent[0]}")

async def create_orchestrator(naptha, orchestrator_config):
    print(f"Orchestrator Config: {orchestrator_config}")
    orchestrator = await naptha.hub.create_orchestrator(orchestrator_config)
    if isinstance(orchestrator, dict):
        print(f"Orchestrator created: {orchestrator}")
    elif isinstance(orchestrator, list):
        print(f"Orchestrator created: {orchestrator[0]}")

async def create_environment(naptha, environment_config):
    print(f"Environment Config: {environment_config}")
    environment = await naptha.hub.create_environment(environment_config)
    if isinstance(environment, dict):
        print(f"Environment created: {environment}")
    elif isinstance(environment, list):
        print(f"Environment created: {environment[0]}")

async def create_persona(naptha, persona_config):
    print(f"Persona Config: {persona_config}")
    persona = await naptha.hub.create_persona(persona_config)
    if isinstance(persona, dict):
        print(f"Persona created: {persona}")
    elif isinstance(persona, list):
        print(f"Persona created: {persona[0]}")

async def create(
        naptha,
        module_name,
        agent_modules = None,
        worker_nodes = None,
        environment_modules = None,
        environment_nodes = None
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
                node=url_to_node(worker_node)
            ) for agent_module, worker_node in zip(agent_modules or [], worker_nodes or [])
        ],
        "environment_deployments": [
            EnvironmentDeployment(
                name=env_module,
                module={"name": env_module},
                node=url_to_node(env_node)
            ) for env_module, env_node in zip(environment_modules or [], environment_nodes or [])
        ]
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
        )
    }

    # Get deployment configuration for module type
    if module_type not in deployment_configs:
        raise ValueError(f"Unsupported module type: {module_type}")

    print(f"Creating {module_type.title()}...")
    deployment = deployment_configs[module_type]()
    result = await naptha.node.create(module_type, deployment)
    print(f"{module_type.title()} creation result: {result}")


async def run(
    naptha,
    module_name,
    parameters=None, 
    worker_nodes=None,
    tool_nodes=None,
    environment_nodes=None,
    kb_nodes=None,
    yaml_file=None, 
    persona_modules=None
):   
    if yaml_file and parameters:
        raise ValueError("Cannot pass both yaml_file and parameters")
    
    if yaml_file:
        parameters = load_yaml_to_dict(yaml_file)

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
    if worker_nodes:
        for worker_node in worker_nodes:
            agent_deployments.append(AgentDeployment(node=NodeConfigUser(ip=worker_node.strip())))
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


    if module_type == "agent":
        print("Running Agent...")

        agent_deployment = AgentDeployment(
            module={"id": module_name, "name": module_name.split(":")[-1], "module_type": module_type}, 
            node=url_to_node(os.getenv("NODE_URL")), 
            config={"persona_module": {"name": persona_modules[0]}} if persona_modules else None,
            tool_deployments=tool_deployments,
            kb_deployments=kb_deployments,
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
            node=url_to_node(os.getenv("NODE_URL")))

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
            kb_deployments=kb_deployments
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
            node=url_to_node(os.getenv("NODE_URL"))
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
            node=url_to_node(os.getenv("NODE_URL"))
        )

        kb_run_input = KBRunInput(
            consumer_id=user['id'],
            inputs=parameters,
            deployment=kb_deployment,
            signature=sign_consumer_id(user['id'], os.getenv("PRIVATE_KEY"))
        )
        kb_run = await naptha.node.run_kb_and_poll(kb_run_input)

async def storage_interaction(naptha, storage_type, operation, path, data=None, schema=None, options=None, file=None):
    """Handle storage interactions using StorageProvider"""
    storage_provider = StorageProvider(naptha.node.node)
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
                    result = await storage_provider.execute(request)
                    return result
                    
            elif operation == "read":
                request = ReadStorageRequest(
                    storage_type=storage_type,
                    path=path,
                    options=json.loads(options) if options else {}
                )
                result = await storage_provider.execute(request)
                
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

        result = await storage_provider.execute(request)
        print(result)
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

def _parse_parameters(args):
    if hasattr(args, 'parameters') and args.parameters is not None:
        try:
            parsed_params = json.loads(args.parameters)
        except json.JSONDecodeError:
            params = shlex.split(args.parameters)
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
        print("Parsed parameters:", parsed_params)
    else:
        parsed_params = None
    return parsed_params

def _parse_str_args(args):
    # Parse all list arguments
    args.worker_nodes = _parse_list_arg(args, 'worker_nodes', default=None)
    args.tool_nodes = _parse_list_arg(args, 'tool_nodes', default=None)
    args.environment_nodes = _parse_list_arg(args, 'environment_nodes', default=None)
    args.kb_nodes = _parse_list_arg(args, 'kb_nodes', default=None)
    args.agent_modules = _parse_list_arg(args, 'agent_modules', default=None)
    args.environment_modules = _parse_list_arg(args, 'environment_modules', default=None)
    args.persona_modules = _parse_list_arg(args, 'persona_modules', default=None)
    args.parameters = _parse_parameters(args)
    return args

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
    agents_parser.add_argument('agent_name', nargs='?', help='Optional agent name')
    agents_parser.add_argument("-p", '--metadata', type=str, help='Metadata in "key=value" format')
    agents_parser.add_argument('-d', '--delete', action='store_true', help='Delete a agent')

    # Orchestrator parser
    orchestrators_parser = subparsers.add_parser("orchestrators", help="List available orchestrators.")
    orchestrators_parser.add_argument('orchestrator_name', nargs='?', help='Optional orchestrator name')
    orchestrators_parser.add_argument("-p", '--metadata', type=str, help='Metadata in "key=value" format')
    orchestrators_parser.add_argument('-d', '--delete', action='store_true', help='Delete an orchestrator')

    # Environment parser
    environments_parser = subparsers.add_parser("environments", help="List available environments.")
    environments_parser.add_argument('environment_name', nargs='?', help='Optional environment name')
    environments_parser.add_argument("-p", '--metadata', type=str, help='Metadata in "key=value" format')
    environments_parser.add_argument('-d', '--delete', action='store_true', help='Delete an environment')

    # Persona parser
    personas_parser = subparsers.add_parser("personas", help="List available personas.")
    personas_parser.add_argument('persona_name', nargs='?', help='Optional persona name')
    personas_parser.add_argument("-p", '--metadata', type=str, help='Metadata in "key=value" format')
    personas_parser.add_argument('-d', '--delete', action='store_true', help='Delete a persona')

    # Tool parser
    tools_parser = subparsers.add_parser("tools", help="List available tools.")
    tools_parser.add_argument('tool_name', nargs='?', help='Optional tool name')
    tools_parser.add_argument("-p", '--metadata', type=str, help='Metadata in "key=value" format')
    tools_parser.add_argument('-d', '--delete', action='store_true', help='Delete a tool')

    # Memory parser
    memories_parser = subparsers.add_parser("memories", help="List available memories.")
    memories_parser.add_argument('memory_name', nargs='?', help='Optional memory name')
    memories_parser.add_argument('-p', '--metadata', type=str, help='Metadata for memory registration in "key=value" format')
    memories_parser.add_argument('-d', '--delete', action='store_true', help='Delete a memory')
    memories_parser.add_argument('-l', '--list', action='store_true', help='List content in a memory')
    memories_parser.add_argument('-a', '--add', action='store_true', help='Add data to a memory')
    memories_parser.add_argument('-c', '--content', type=str, help='Content to add to a memory', required=False)
    memories_parser.add_argument('-m', '--memory_node_urls', type=str, help='Memory node URLs', default=["http://localhost:7001"])

    # Knowledge base parser
    kbs_parser = subparsers.add_parser("kbs", help="List available knowledge bases.")
    kbs_parser.add_argument('kb_name', nargs='?', help='Optional knowledge base name')
    kbs_parser.add_argument('-p', '--metadata', type=str, help='Metadata for knowledge base registration in "key=value" format')
    kbs_parser.add_argument('-d', '--delete', action='store_true', help='Delete a knowledge base')
    kbs_parser.add_argument('-k', '--kb_nodes', type=str, help='Knowledge base node URLs')

    # Create parser
    create_parser = subparsers.add_parser("create", help="Execute create command.")
    create_parser.add_argument("module", help="Select the module to create")
    create_parser.add_argument("-a", "--agent_modules", help="Agent modules to create")
    create_parser.add_argument("-n", "--worker_nodes", help="Agent nodes to take part in orchestrator runs.")
    create_parser.add_argument("-e", "--environment_modules", help="Environment module to create")
    create_parser.add_argument("-m", "--environment_nodes", help="Environment nodes to store data during agent runs.")

    # Run parser
    run_parser = subparsers.add_parser("run", help="Execute run command.")
    run_parser.add_argument("agent", help="Select the agent to run")
    run_parser.add_argument("-p", '--parameters', type=str, help='Parameters in "key=value" format')
    run_parser.add_argument("-n", "--worker_nodes", help="Worker nodes to take part in agent runs.")
    run_parser.add_argument("-t", "--tool_nodes", help="Tool nodes to take part in agent runs.")
    run_parser.add_argument("-e", "--environment_nodes", help="Environment nodes to store data during agent runs.")
    run_parser.add_argument('-k', '--kb_nodes', type=str, help='Knowledge base nodes')
    run_parser.add_argument('-m', '--memory_nodes', type=str, help='Memory nodes')
    run_parser.add_argument("-pm", "--persona_modules", help="Personas URLs to install before running the agent")
    run_parser.add_argument("-f", "--file", help="YAML file with agent run parameters")

    # Inference parser
    inference_parser = subparsers.add_parser("inference", help="Run model inference.")
    inference_parser.add_argument("prompt", help="Input prompt for the model")
    inference_parser.add_argument("-m", "--model", help="Model to use for inference", default="phi3:mini")
    inference_parser.add_argument("-p", "--parameters", type=str, help='Additional model parameters in "key=value" format')

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
        
    async with naptha as naptha:
        args = parser.parse_args()
        args = _parse_str_args(args)
        print(args)
        if args.command == "signup":
            _, _ = await user_setup_flow(hub_url, public_key)
        elif args.command in [
            "nodes", "agents", "orchestrators", "environments", 
            "personas", "kbs", "memories", "tools", "run", "inference", 
            "publish", "create", "storage"
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
                if not args.agent_name:
                    await list_agents(naptha)
                elif args.delete and len(args.agent_name.split()) == 1:
                    await naptha.hub.delete_agent(args.agent_name)
                elif len(args.agent_name.split()) == 1:
                    if hasattr(args, 'metadata') and args.metadata is not None:
                        params = shlex.split(args.metadata)
                        parsed_params = {}
                        for param in params:
                            key, value = param.split('=')
                            parsed_params[key] = value

                        required_metadata = ['description', 'parameters', 'module_url']
                        missing_metadata = [param for param in required_metadata if param not in parsed_params]
                        if missing_metadata:
                            print(f"Missing required metadata: {', '.join(missing_metadata)}")
                            return
                        agent_config = {
                            "id": f"agent:{args.agent_name}",
                            "name": args.agent_name,
                            "description": parsed_params['description'],
                            "parameters": parsed_params['parameters'],
                            "author": f"user:{naptha.hub.public_key}",
                            "module_url": parsed_params['module_url'],
                            "module_type": parsed_params.get('module_type', 'agent'),
                            "module_version": parsed_params.get('module_version', '0.1'),
                            "module_entrypoint": parsed_params.get('module_entrypoint', 'run.py'),
                            "execution_type": parsed_params.get('execution_type', 'package')
                        }
                        await create_agent(naptha, agent_config)
                else:
                    print("Invalid command.")
            elif args.command == "orchestrators":
                if not args.orchestrator_name:
                    await list_orchestrators(naptha)
                elif args.delete and len(args.orchestrator_name.split()) == 1:
                    await naptha.hub.delete_orchestrator(args.orchestrator_name)
                elif len(args.orchestrator_name.split()) == 1:
                    if hasattr(args, 'metadata') and args.metadata is not None:
                        params = shlex.split(args.metadata)
                        parsed_params = {}
                        for param in params:
                            key, value = param.split('=')
                            parsed_params[key] = value

                        required_metadata = ['description', 'parameters', 'module_url']
                        if not all(param in parsed_params for param in required_metadata):
                            print(f"Missing one or more of the following required metadata: {required_metadata}")
                            return
                            
                        orchestrator_config = {
                            "id": f"orchestrator:{args.orchestrator_name}",
                            "name": args.orchestrator_name,
                            "description": parsed_params['description'],
                            "parameters": parsed_params['parameters'],
                            "author": f"user:{naptha.hub.public_key}",
                            "module_url": parsed_params['module_url'],
                            "module_type": parsed_params.get('module_type', 'orchestrator'),
                            "module_version": parsed_params.get('module_version', '0.1'),
                            "module_entrypoint": parsed_params.get('module_entrypoint', 'run.py'),
                            "execution_type": parsed_params.get('execution_type', 'package')
                        }
                        await create_orchestrator(naptha, orchestrator_config)
                else:
                    print("Invalid command.")
            elif args.command == "environments":
                if not args.environment_name:
                    await list_environments(naptha)
                elif args.delete and len(args.environment_name.split()) == 1:
                    await naptha.hub.delete_environment(args.environment_name)
                elif len(args.environment_name.split()) == 1:
                    if hasattr(args, 'metadata') and args.metadata is not None:
                        params = shlex.split(args.metadata)
                        parsed_params = {}
                        for param in params:
                            key, value = param.split('=')
                            parsed_params[key] = value

                        required_metadata = ['description', 'parameters', 'module_url']
                        if not all(param in parsed_params for param in required_metadata):
                            print(f"Missing one or more of the following required metadata: {required_metadata}")
                            return
                            
                        environment_config = {
                            "id": f"environment:{args.environment_name}",
                            "name": args.environment_name,
                            "description": parsed_params['description'],
                            "parameters": parsed_params['parameters'],
                            "author": f"user:{naptha.hub.public_key}",
                            "module_url": parsed_params['module_url'],
                            "module_type": parsed_params.get('module_type', 'environment'),
                            "module_version": parsed_params.get('module_version', '0.1'),
                            "module_entrypoint": parsed_params.get('module_entrypoint', 'run.py'),
                            "execution_type": parsed_params.get('execution_type', 'package')
                        }
                        await create_environment(naptha, environment_config)
                else:
                    print("Invalid command.")
            elif args.command == "tools":
                if not args.tool_name:
                    await list_tools(naptha)
                elif args.delete and len(args.tool_name.split()) == 1:
                    await naptha.hub.delete_tool(args.tool_name)
                elif len(args.tool_name.split()) == 1:
                    if hasattr(args, 'metadata') and args.metadata is not None:
                        params = shlex.split(args.metadata)
                        parsed_params = {}
                        for param in params:
                            key, value = param.split('=')
                            parsed_params[key] = value

                        required_metadata = ['description', 'parameters', 'module_url']
                        if not all(param in parsed_params for param in required_metadata):
                            print(f"Missing one or more of the following required metadata: {required_metadata}")
                            return
                            
                        tool_config = {
                            "id": f"tool:{args.tool_name}",
                            "name": args.tool_name,
                            "description": parsed_params['description'],
                            "parameters": parsed_params['parameters'],
                            "author": f"user:{naptha.hub.public_key}",
                            "module_url": parsed_params['module_url'],
                            "module_type": parsed_params.get('module_type', 'tool'),
                            "module_version": parsed_params.get('module_version', '0.1'),
                            "module_entrypoint": parsed_params.get('module_entrypoint', 'run.py'),
                            "execution_type": parsed_params.get('execution_type', 'package')
                        }
                        await naptha.hub.create_tool(tool_config)
                else:
                    print("Invalid command.")
            elif args.command == "personas":
                if not args.persona_name:
                    await list_personas(naptha)
                elif args.delete and len(args.persona_name.split()) == 1:
                    await naptha.hub.delete_persona(args.persona_name)
                elif len(args.persona_name.split()) == 1:
                    if hasattr(args, 'metadata') and args.metadata is not None:
                        params = shlex.split(args.metadata)
                        parsed_params = {}
                        for param in params:
                            key, value = param.split('=')
                            parsed_params[key] = value

                        required_metadata = ['description', 'parameters', 'module_url']
                        if not all(param in parsed_params for param in required_metadata):
                            print(f"Missing one or more of the following required metadata: {required_metadata}")
                            return
                            
                        persona_config = {
                            "id": f"persona:{args.persona_name}",
                            "name": args.persona_name,
                            "description": parsed_params['description'],
                            "parameters": parsed_params['parameters'],
                            "author": f"user:{naptha.hub.public_key}",
                            "module_url": parsed_params['module_url'],
                            "module_type": parsed_params.get('module_type', 'persona'),
                            "module_version": parsed_params.get('module_version', '0.1'),
                            "module_entrypoint": parsed_params.get('module_entrypoint', 'run.py'),
                            "execution_type": parsed_params.get('execution_type', 'package')
                        }
                        await create_persona(naptha, persona_config)
                else:
                    print("Invalid command.")
            elif args.command == "memories":
                if not args.memory_name:
                    # List all memories
                    await list_memories(naptha)
                elif args.list:
                    # List content of specific memory
                    await list_memory_content(naptha, args.memory_name)
                elif args.add:
                    # Add data to memory
                    if not args.content:
                        console = Console()
                        console.print("[red]Data is required for add command.[/red]")
                        return
                    await add_data_to_memory(naptha, args.memory_name, args.content, user_id=f"user:{naptha.hub.public_key}", memory_node_url=args.memory_node_urls[0])
                elif args.delete and len(args.memory_name.split()) == 1:
                    await naptha.hub.delete_memory(args.memory_name)
                elif len(args.memory_name.split()) == 1:
                    if hasattr(args, 'metadata') and args.metadata is not None:
                        params = shlex.split(args.metadata)
                        parsed_params = {}
                        for param in params:
                            key, value = param.split('=')
                            parsed_params[key] = value

                        required_metadata = ['description', 'parameters', 'module_url']
                        if not all(param in parsed_params for param in required_metadata):
                            print(f"Missing one or more of the following required metadata: {required_metadata}")
                            return
                            
                        memory_config = {
                            "id": f"memory:{args.memory_name}",
                            "name": args.memory_name,
                            "description": parsed_params['description'],
                            "parameters": parsed_params['parameters'],
                            "author": f"user:{naptha.hub.public_key}",
                            "module_url": parsed_params['module_url'],
                            "module_type": parsed_params.get('module_type', 'memory'),
                            "module_version": parsed_params.get('module_version', '0.1'),
                            "module_entrypoint": parsed_params.get('module_entrypoint', 'run.py'),
                            "execution_type": parsed_params.get('execution_type', 'package')
                        }
                        await naptha.hub.create_memory(memory_config)
                else:
                    # Show specific memory info
                    await list_memories(naptha, args.memory_name)
            elif args.command == "kbs":
                if not args.kb_name:
                    # List all knowledge bases
                    await list_kbs(naptha)
                elif args.delete and len(args.kb_name.split()) == 1:
                    await naptha.hub.delete_kb(args.kb_name)
                elif len(args.kb_name.split()) == 1:
                    if hasattr(args, 'metadata') and args.metadata is not None:
                        params = shlex.split(args.metadata)
                        parsed_params = {}
                        for param in params:
                            key, value = param.split('=')
                            parsed_params[key] = value

                        required_metadata = ['description', 'parameters', 'module_url']
                        if not all(param in parsed_params for param in required_metadata):
                            print(f"Missing one or more of the following required metadata: {required_metadata}")
                            return
                            
                        kb_config = {
                            "id": f"kb:{args.kb_name}",
                            "name": args.kb_name,
                            "description": parsed_params['description'],
                            "parameters": parsed_params['parameters'],
                            "author": f"user:{naptha.hub.public_key}",
                            "module_url": parsed_params['module_url'],
                            "module_type": parsed_params.get('module_type', 'kb'),
                            "module_version": parsed_params.get('module_version', '0.1'),
                            "module_entrypoint": parsed_params.get('module_entrypoint', 'run.py'),
                            "execution_type": parsed_params.get('execution_type', 'package')
                        }
                        await naptha.hub.create_kb(kb_config)
                else:
                    # Show specific knowledge base info
                    await list_kbs(naptha, args.kb_name)
            elif args.command == "create":
                await create(naptha, args.module, args.agent_modules, args.worker_nodes, args.environment_modules, args.environment_nodes)
            elif args.command == "run":                    
                await run(naptha, args.agent, args.parameters, args.worker_nodes, args.tool_nodes, args.environment_nodes, args.kb_nodes, args.file, args.persona_modules)
            elif args.command == "inference":
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
        else:
            parser.print_help()

def cli():
    import sys
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    cli()