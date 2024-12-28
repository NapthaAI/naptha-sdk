import argparse
import asyncio
from dotenv import load_dotenv
from naptha_sdk.client.naptha import Naptha
from naptha_sdk.client.hub import user_setup_flow
from naptha_sdk.user import get_public_key
from naptha_sdk.schemas import AgentConfig, AgentDeployment, EnvironmentDeployment, OrchestratorDeployment, OrchestratorRunInput, EnvironmentRunInput, NodeSchema
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
from naptha_sdk.schemas import AgentConfig, AgentDeployment, ChatCompletionRequest, EnvironmentDeployment, \
    OrchestratorDeployment, OrchestratorRunInput, EnvironmentRunInput, KBDeployment, KBRunInput, ToolDeployment, ToolRunInput
from naptha_sdk.user import get_public_key
from naptha_sdk.utils import url_to_node

load_dotenv(override=True)

def load_yaml_to_dict(file_path):
    with open(file_path, 'r') as file:
        # Load the YAML content into a Python dictionary
        yaml_content = yaml.safe_load(file)
    return yaml_content

def creds(naptha):
    return naptha.services.show_credits()

def list_services(naptha):
    services = naptha.services.list_services()
    for service in services:
        print(service) 

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
    
    # Add columns with appropriate formatting
    for header in headers:
        table.add_column(
            header,
            overflow="fold",
            max_width=60,
            justify="left",
            no_wrap=False
        )

    # Add rows
    for node in nodes:
        table.add_row(*[str(node.get(key, '')) for key in headers])

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
    table.add_column("Module Type", justify="left")
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
            agent['module_type'],
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
    table.add_column("Module Type", justify="left")
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
            tool['module_type'],
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
    table.add_column("Module Type", justify="left")
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
            orchestrator['module_type'],
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
    table.add_column("Module Type", justify="left")
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
            environment['module_type'],
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
    table.add_column("Module URL", justify="left", max_width=40)
    table.add_column("Module Version", justify="center")

    # Add rows
    for persona in personas:
        table.add_row(
            persona['name'],
            persona['id'],
            persona['author'],
            persona['description'],
            persona['module_url'],
            persona['module_version'],
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
    table.add_column("Module Type", justify="left")
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
            memory['module_type'],
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

async def list_kb_content(naptha, kb_name):
    rows = await naptha.node.query_table(
        table_name=kb_name,   
        columns="*",
        condition=None,
        order_by=None,
        limit=None
    )
    
    if not rows.get('rows'):
        console = Console()
        console.print("[red]No content found in knowledge base.[/red]")
        return

    console = Console()
    table = Table(
        box=box.ROUNDED,
        show_lines=True,
        title=f"Knowledge Base Content: {kb_name}",
        title_style="bold cyan",
        header_style="bold blue",
        row_styles=["", "dim"]  # Alternating row styles
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

async def add_data_to_kb(naptha, kb_name, data, user_id=None, kb_node=None):
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
        
        kb_run_input = {
            "consumer_id": user_id,
            "inputs": {
                "mode": "add_data",
                "data": json.dumps(data_dict)
            },
            "deployment": {
                "name": kb_name,
                "module": {
                    "name": kb_name
                },
                "node": url_to_node(kb_node)
            }
        }

        kb_run = await naptha.node.run_kb_and_poll(kb_run_input)
        console = Console()
        console.print(f"\n[green]Successfully added data to knowledge base:[/green] {kb_name}")
        console.print(kb_run)
        
    except Exception as e:
        console = Console()
        console.print(f"\n[red]Error adding data to knowledge base:[/red] {str(e)}")

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
    user_id,
    parameters=None, 
    worker_nodes=None,
    tool_nodes=None,
    environment_nodes=None,
    kb_nodes=None,
    yaml_file=None, 
    personas_urls=None
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
            agent_deployments.append(AgentDeployment(node=NodeSchema(ip=worker_node.strip())))
    tool_deployments = []
    if tool_nodes:
        for tool_node in tool_nodes:
            tool_deployments.append(ToolDeployment(node=NodeSchema(ip=tool_node.strip())))
    environment_deployments = []
    if environment_nodes:
        for environment_node in environment_nodes:
            environment_deployments.append(EnvironmentDeployment(node=NodeSchema(ip=environment_node.strip())))
    kb_deployments = []
    if kb_nodes:
        for kb_node in kb_nodes:
            kb_deployments.append(KBDeployment(node=NodeSchema(ip=kb_node.strip())))


    if module_type == "agent":
        print("Running Agent...")

        agent_deployment = AgentDeployment(
            module={"id": module_name, "name": module_name.split(":")[-1]}, 
            node=url_to_node(os.getenv("NODE_URL")), 
            tool_deployments=tool_deployments,
            kb_deployments=kb_deployments,
            environment_deployments=environment_deployments
        )

        agent_run_input = {
            'consumer_id': user_id,
            "inputs": parameters,
            "deployment": agent_deployment.model_dump(),
            "personas_urls": personas_urls
        }
        print(f"Agent run input: {agent_run_input}")

        agent_run = await naptha.node.run_agent_and_poll(agent_run_input)

    elif module_type == "tool":
        print("Running Tool...")
        tool_deployment = ToolDeployment(
            module={"id": module_name, "name": module_name.split(":")[-1]},
            node=url_to_node(os.getenv("NODE_URL")))

        tool_run_input = ToolRunInput(
            consumer_id=user_id,
            inputs=parameters,
            deployment=tool_deployment
        )
        tool_run = await naptha.node.run_tool_and_poll(tool_run_input)

    elif module_type == "orchestrator":
        print("Running Orchestrator...")

        orchestrator_deployment = OrchestratorDeployment(
            module={"id": module_name, "name": module_name.split(":")[-1]}, 
            node=url_to_node(os.getenv("NODE_URL")),
            agent_deployments=agent_deployments,
            environment_deployments=environment_deployments,
            kb_deployments=kb_deployments
        )

        orchestrator_run_input = OrchestratorRunInput(
            consumer_id=user_id,
            inputs=parameters,
            deployment=orchestrator_deployment
        )
        orchestrator_run = await naptha.node.run_orchestrator_and_poll(orchestrator_run_input)

    elif module_type == "environment":
        print("Running Environment...")

        environment_deployment = EnvironmentDeployment(
            module={"id": module_name, "name": module_name.split(":")[-1]}, 
            node=url_to_node(os.getenv("NODE_URL"))
        )

        environment_run_input = EnvironmentRunInput(
            inputs=parameters,
            deployment=environment_deployment,
            consumer_id=user_id,
        )
        environment_run = await naptha.node.run_environment_and_poll(environment_run_input)

    elif module_type == "kb":
        print("Running Knowledge Base...")

        kb_deployment = KBDeployment(
            module={"id": module_name, "name": module_name.split(":")[-1]}, 
            node=url_to_node(os.getenv("NODE_URL"))
        )

        kb_run_input = KBRunInput(
            consumer_id=user_id,
            inputs=parameters,
            deployment=kb_deployment
        )
        kb_run = await naptha.node.run_kb_and_poll(kb_run_input)

async def read_storage(naptha, hash_or_name, output_dir='./files', ipfs=False):
    """Read from storage, IPFS, or IPNS."""
    try:
        await naptha.node.read_storage(hash_or_name.strip(), output_dir, ipfs=ipfs)
    except Exception as err:
        print(f"Error: {err}")

async def write_storage(naptha, storage_input, ipfs=False, publish_to_ipns=False, update_ipns_name=None):
    """Write to storage, optionally to IPFS and/or IPNS."""
    try:
        response = await naptha.node.write_storage(storage_input, ipfs=ipfs, publish_to_ipns=publish_to_ipns, update_ipns_name=update_ipns_name)
        print(response)
    except Exception as err:
        print(f"Error: {err}")

def _parse_list_arg(args, arg_name, default=None, split_char=','):
    """Helper function to parse list arguments with common logic."""
    if hasattr(args, arg_name) and getattr(args, arg_name) is not None:
        value = getattr(args, arg_name)
        return value.split(split_char) if split_char in value else [value]
    return default

def _parse_str_args(args):
    # Parse all list arguments
    args.worker_nodes = _parse_list_arg(args, 'worker_nodes', default=None)
    args.tool_nodes = _parse_list_arg(args, 'tool_nodes', default=None)
    args.environment_nodes = _parse_list_arg(args, 'environment_nodes', default=None)
    args.kb_nodes = _parse_list_arg(args, 'kb_nodes', default=None)
    args.agent_modules = _parse_list_arg(args, 'agent_modules', default=None)
    args.environment_modules = _parse_list_arg(args, 'environment_modules', default=None)
    args.personas_urls = _parse_list_arg(args, 'personas_urls', default=None)
    return args

async def main():
    public_key = get_public_key(os.getenv("PRIVATE_KEY")) if os.getenv("PRIVATE_KEY") else None
    hub_username = os.getenv("HUB_USERNAME")
    hub_password = os.getenv("HUB_PASSWORD")
    hub_url = os.getenv("HUB_URL")

    naptha = Naptha()

    parser = argparse.ArgumentParser(description="CLI with for Naptha")
    subparsers = parser.add_subparsers(title="commands", dest="command")

    # Node commands
    nodes_parser = subparsers.add_parser("nodes", help="List available nodes.")
    nodes_parser.add_argument("-s", '--list_servers', action='store_true', help='List servers')

    # Agent commands
    agents_parser = subparsers.add_parser("agents", help="List available agents.")
    agents_parser.add_argument('agent_name', nargs='?', help='Optional agent name')
    agents_parser.add_argument("-p", '--metadata', type=str, help='Metadata in "key=value" format')
    agents_parser.add_argument('-d', '--delete', action='store_true', help='Delete a agent')

    # Orchestrator commands
    orchestrators_parser = subparsers.add_parser("orchestrators", help="List available orchestrators.")
    orchestrators_parser.add_argument('orchestrator_name', nargs='?', help='Optional orchestrator name')
    orchestrators_parser.add_argument("-p", '--metadata', type=str, help='Metadata in "key=value" format')
    orchestrators_parser.add_argument('-d', '--delete', action='store_true', help='Delete an orchestrator')

    # Environment commands
    environments_parser = subparsers.add_parser("environments", help="List available environments.")
    environments_parser.add_argument('environment_name', nargs='?', help='Optional environment name')
    environments_parser.add_argument("-p", '--metadata', type=str, help='Metadata in "key=value" format')
    environments_parser.add_argument('-d', '--delete', action='store_true', help='Delete an environment')

    # Persona commands
    personas_parser = subparsers.add_parser("personas", help="List available personas.")
    personas_parser.add_argument('persona_name', nargs='?', help='Optional persona name')
    personas_parser.add_argument("-p", '--metadata', type=str, help='Metadata in "key=value" format')
    personas_parser.add_argument('-d', '--delete', action='store_true', help='Delete a persona')

    # Tool commands
    tools_parser = subparsers.add_parser("tools", help="List available tools.")
    tools_parser.add_argument('tool_name', nargs='?', help='Optional tool name')
    tools_parser.add_argument("-p", '--metadata', type=str, help='Metadata in "key=value" format')
    tools_parser.add_argument('-d', '--delete', action='store_true', help='Delete a tool')

    # Memory commands
    memories_parser = subparsers.add_parser("memories", help="List available memories.")
    memories_parser.add_argument('memory_name', nargs='?', help='Optional memory name')
    memories_parser.add_argument('-p', '--metadata', type=str, help='Metadata for memory registration in "key=value" format')
    memories_parser.add_argument('-d', '--delete', action='store_true', help='Delete a memory')
    memories_parser.add_argument('-l', '--list', action='store_true', help='List content in a memory')
    memories_parser.add_argument('-a', '--add', action='store_true', help='Add data to a memory')
    memories_parser.add_argument('-c', '--content', type=str, help='Content to add to a memory', required=False)
    memories_parser.add_argument('-m', '--memory_node_urls', type=str, help='Memory node URLs', default=["http://localhost:7001"])

    # Knowledge base commands
    kbs_parser = subparsers.add_parser("kbs", help="List available knowledge bases.")
    kbs_parser.add_argument('kb_name', nargs='?', help='Optional knowledge base name')
    kbs_parser.add_argument('-p', '--metadata', type=str, help='Metadata for knowledge base registration in "key=value" format')
    kbs_parser.add_argument('-d', '--delete', action='store_true', help='Delete a knowledge base')
    kbs_parser.add_argument('-l', '--list', action='store_true', help='List content in a knowledge base')
    kbs_parser.add_argument('-a', '--add', action='store_true', help='Add data to a knowledge base')
    kbs_parser.add_argument('-c', '--content', type=str, help='Content to add to a knowledge base', required=False)
    kbs_parser.add_argument('-k', '--kb_nodes', type=str, help='Knowledge base node URLs')

    # Create command
    create_parser = subparsers.add_parser("create", help="Execute create command.")
    create_parser.add_argument("module", help="Select the module to create")
    create_parser.add_argument("-a", "--agent_modules", help="Agent modules to create")
    create_parser.add_argument("-n", "--worker_nodes", help="Agent nodes to take part in orchestrator runs.")
    create_parser.add_argument("-e", "--environment_modules", help="Environment module to create")
    create_parser.add_argument("-m", "--environment_nodes", help="Environment nodes to store data during agent runs.")

    # Run command
    run_parser = subparsers.add_parser("run", help="Execute run command.")
    run_parser.add_argument("agent", help="Select the agent to run")
    run_parser.add_argument("-p", '--parameters', type=str, help='Parameters in "key=value" format')
    run_parser.add_argument("-n", "--worker_nodes", help="Worker nodes to take part in agent runs.")
    run_parser.add_argument("-t", "--tool_nodes", help="Tool nodes to take part in agent runs.")
    run_parser.add_argument("-e", "--environment_nodes", help="Environment nodes to store data during agent runs.")
    run_parser.add_argument('-k', '--kb_nodes', type=str, help='Knowledge base nodes')
    run_parser.add_argument('-m', '--memory_nodes', type=str, help='Memory nodes')
    
    run_parser.add_argument("-u", "--personas_urls", help="Personas URLs to install before running the agent")
    run_parser.add_argument("-f", "--file", help="YAML file with agent run parameters")

    # Inference command
    inference_parser = subparsers.add_parser("inference", help="Run model inference.")
    inference_parser.add_argument("prompt", help="Input prompt for the model")
    inference_parser.add_argument("-m", "--model", help="Model to use for inference", default="phi3:mini")
    inference_parser.add_argument("-p", "--parameters", type=str, help='Additional model parameters in "key=value" format')

    # Read storage commands
    read_storage_parser = subparsers.add_parser("read_storage", help="Read from storage.")
    read_storage_parser.add_argument("-id", "--agent_run_id", help="Agent run ID to read from")
    read_storage_parser.add_argument("-o", "--output_dir", default="files", help="Output directory to write to")
    read_storage_parser.add_argument("--ipfs", help="Read from IPFS", action="store_true")

    # Write storage commands
    write_storage_parser = subparsers.add_parser("write_storage", help="Write to storage.")
    write_storage_parser.add_argument("-i", "--storage_input", help="Path to file or directory to write to storage")
    write_storage_parser.add_argument("--ipfs", help="Write to IPFS", action="store_true")
    write_storage_parser.add_argument("--publish_to_ipns", help="Publish to IPNS", action="store_true")
    write_storage_parser.add_argument("--update_ipns_name", help="Update IPNS name")

    # Signup command
    signup_parser = subparsers.add_parser("signup", help="Sign up a new user.")

    # Publish command
    publish_parser = subparsers.add_parser("publish", help="Publish agents.")

    async with naptha as naptha:
        args = parser.parse_args()
        args = _parse_str_args(args)
        if args.command == "signup":
            _, user_id = await user_setup_flow(hub_url, public_key)
        elif args.command in ["nodes", "agents", "orchestrators", "environments", "personas", "kbs", "memories", "tools", "run", "inference", "read_storage", "write_storage", "publish", "create"]:
            if not naptha.hub.is_authenticated:
                if not hub_username or not hub_password:
                    print(
                        "Please set HUB_USERNAME and HUB_PASSWORD environment variables or sign up first (run naptha signup).")
                    return
                _, _, user_id = await naptha.hub.signin(hub_username, hub_password)

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
                            "author": naptha.hub.user_id,
                            "module_url": parsed_params['module_url'],
                            "module_type": parsed_params.get('module_type', 'package'),
                            "module_version": parsed_params.get('module_version', '0.1'),
                            "module_entrypoint": parsed_params.get('module_entrypoint', 'run.py')
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
                            "author": naptha.hub.user_id,
                            "module_url": parsed_params['module_url'],
                            "module_type": parsed_params.get('module_type', 'package'),
                            "module_version": parsed_params.get('module_version', '0.1'),
                            "module_entrypoint": parsed_params.get('module_entrypoint', 'run.py')
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
                            "author": naptha.hub.user_id,
                            "module_url": parsed_params['module_url'],
                            "module_type": parsed_params.get('module_type', 'package'),
                            "module_version": parsed_params.get('module_version', '0.1'),
                            "module_entrypoint": parsed_params.get('module_entrypoint', 'run.py')
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
                            "author": naptha.hub.user_id,
                            "module_url": parsed_params['module_url'],
                            "module_type": parsed_params.get('module_type', 'package'),
                            "module_version": parsed_params.get('module_version', '0.1'),
                            "module_entrypoint": parsed_params.get('module_entrypoint', 'run.py')
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

                        required_metadata = ['description', 'module_url']
                        if not all(param in parsed_params for param in required_metadata):
                            print(f"Missing one or more of the following required metadata: {required_metadata}")
                            return
                            
                        persona_config = {
                            "id": f"persona:{args.persona_name}",
                            "name": args.persona_name,
                            "description": parsed_params['description'],
                            "author": naptha.hub.user_id,
                            "module_url": parsed_params['module_url'],
                            "module_version": parsed_params.get('module_version', '0.1'),
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
                    await add_data_to_memory(naptha, args.memory_name, args.content, user_id=user_id, memory_node_url=args.memory_node_urls[0])
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
                            "author": naptha.hub.user_id,
                            "module_url": parsed_params['module_url'],
                            "module_type": parsed_params.get('module_type', 'package'),
                            "module_version": parsed_params.get('module_version', '0.1'),
                            "module_entrypoint": parsed_params.get('module_entrypoint', 'run.py')
                        }
                        await naptha.hub.create_memory(memory_config)
                else:
                    # Show specific memory info
                    await list_memories(naptha, args.memory_name)
            elif args.command == "kbs":
                if not args.kb_name:
                    # List all knowledge bases
                    await list_kbs(naptha)
                elif args.list:
                    # List content of specific knowledge base
                    await list_kb_content(naptha, args.kb_name)
                elif args.add:
                    # Add data to knowledge base
                    if not args.content:
                        console = Console()
                        console.print("[red]Data is required for add command.[/red]")
                        return
                    await add_data_to_kb(naptha, args.kb_name, args.content, user_id=user_id, kb_node=os.getenv("NODE_URL"))
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
                            "author": naptha.hub.user_id,
                            "module_url": parsed_params['module_url'],
                            "module_type": parsed_params.get('module_type', 'package'),
                            "module_version": parsed_params.get('module_version', '0.1'),
                            "module_entrypoint": parsed_params.get('module_entrypoint', 'run.py')
                        }
                        await naptha.hub.create_kb(kb_config)
                else:
                    # Show specific knowledge base info
                    await list_kbs(naptha, args.kb_name)

            elif args.command == "create":
                await create(naptha, args.module, args.agent_modules, args.worker_nodes, args.environment_modules, args.environment_nodes)
            
            elif args.command == "run":
                if hasattr(args, 'parameters') and args.parameters is not None:
                    try:
                        parsed_params = json.loads(args.parameters)
                    except json.JSONDecodeError:
                        params = shlex.split(args.parameters)
                        parsed_params = {}
                        for param in params:
                            key, value = param.split('=')
                            parsed_params[key] = value
                else:
                    parsed_params = None
                    
                await run(naptha, args.agent, user_id, parsed_params, args.worker_nodes, args.tool_nodes, args.environment_nodes, args.kb_nodes, args.file, args.personas_urls)
            elif args.command == "inference":
                request = ChatCompletionRequest(
                    messages=[{"role": "user", "content": args.prompt}],
                    model=args.model,
                )
                await naptha.node.run_inference(request)
            elif args.command == "read_storage":
                await read_storage(naptha, args.agent_run_id, args.output_dir, args.ipfs)
            elif args.command == "write_storage":
                await write_storage(naptha, args.storage_input, args.ipfs, args.publish_to_ipns, args.update_ipns_name)

                
            elif args.command == "publish":
                await naptha.publish_agents()
        else:
            parser.print_help()

def cli():
    asyncio.run(main())

if __name__ == "__main__":
    asyncio.run(main())