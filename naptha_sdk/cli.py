import argparse
import asyncio
from dotenv import load_dotenv
from naptha_sdk.client.naptha import Naptha
from naptha_sdk.client.hub import user_setup_flow
from naptha_sdk.user import get_public_key
from naptha_sdk.schemas import AgentRun
import os
import shlex
import time
import yaml
import json
from tabulate import tabulate
from textwrap import wrap

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
        print("No nodes found.")
        return

    # Determine available keys
    keys = list(nodes[0].keys())

    # Create headers and table data based on available keys
    headers = keys
    table_data = []

    for node in nodes:
        row = []
        for key in keys:
            value = str(node.get(key, ''))
            if len(value) > 50:
                wrapped_value = '\n'.join(wrap(value, width=50))
                row.append(wrapped_value)
            else:
                row.append(value)
        table_data.append(row)

    print("\nAll Nodes:")
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    print(f"\nTotal nodes: {len(nodes)}")

async def list_agents(naptha):
    agents = await naptha.hub.list_agents()
    
    if not agents:
        print("No agents found.")
        return

    headers = ["Name", "ID", "Type", "Version", "Author", "Description"]
    table_data = []

    for agent in agents:
        # Wrap the description text
        wrapped_description = '\n'.join(wrap(agent['description'], width=50))
        
        row = [
            agent['name'],
            agent['id'],
            agent['type'],
            agent['version'],
            agent['author'],
            wrapped_description
        ]
        table_data.append(row)

    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    print(f"\nTotal agents: {len(agents)}")

async def create_agent(naptha, agent_config):
    print(f"Agent Config: {agent_config}")
    agent = await naptha.hub.create_agent(agent_config)
    if isinstance(agent, dict):
        print(f"Agent created: {agent}")
    elif isinstance(agent, list):
        print(f"Agent created: {agent[0]}")

async def run(
    naptha, 
    agent_name, 
    user_id,
    parameters=None, 
    worker_nodes=None,
    yaml_file=None, 
):   
    if yaml_file and parameters:
        raise ValueError("Cannot pass both yaml_file and parameters")
    
    if yaml_file:
        parameters = load_yaml_to_dict(yaml_file)

    agent_run_input = {
        'consumer_id': user_id,
        "agent_name": agent_name,
        'worker_nodes': worker_nodes,
        "agent_run_params": parameters,
    }
    
    user = await naptha.node.check_user(user_input={"public_key": naptha.hub.public_key})

    if user['is_registered'] == True:
        print("Found user...", user)
    else:
        print("No user found. Registering user...")
        user = await naptha.node.register_user(user_input=user)
        print(f"User registered: {user}.")

    print("Running...")
    agent_run = await naptha.node.run_agent(agent_run_input)

    if agent_run.status == 'completed':
        print("Agent run completed successfully.")
        print("Results: ", agent_run.results)
    else:
        print("Agent run failed.")
        print(agent_run.error_message)

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

async def main():
    public_key = get_public_key(os.getenv("PRIVATE_KEY")) if os.getenv("PRIVATE_KEY") else None
    hub_username = os.getenv("HUB_USER")
    hub_password = os.getenv("HUB_PASS")
    hub_url = os.getenv("HUB_URL")

    naptha = Naptha()

    parser = argparse.ArgumentParser(description="CLI with for Naptha")
    subparsers = parser.add_subparsers(title="commands", dest="command")

    # Node commands
    nodes_parser = subparsers.add_parser("nodes", help="List available nodes.")

    # Agent commands
    agents_parser = subparsers.add_parser("agents", help="List available agents.")
    agents_parser.add_argument('agent_name', nargs='?', help='Optional agent name')
    agents_parser.add_argument("-p", '--parameters', type=str, help='Parameters in "key=value" format')
    agents_parser.add_argument('-d', '--delete', action='store_true', help='Delete a agent')

    # Run command
    run_parser = subparsers.add_parser("run", help="Execute run command.")
    run_parser.add_argument("agent", help="Select the agent to run")
    run_parser.add_argument("-p", '--parameters', type=str, help='Parameters in "key=value" format')
    run_parser.add_argument("-n", "--worker_nodes", help="Worker nodes to take part in agent runs.")
    run_parser.add_argument("-f", "--file", help="YAML file with agent run parameters")

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
        if args.command == "signup":
            _, user_id = await user_setup_flow(hub_url, public_key)
        elif args.command in ["nodes", "agents", "run", "read_storage", "write_storage", "publish"]:
            if not naptha.hub.is_authenticated:
                if not hub_username or not hub_password:
                    print("Please set HUB_USER and HUB_PASS environment variables or sign up first (run naptha signup).")
                    return
                _, _, user_id = await naptha.hub.signin(hub_username, hub_password)

            if args.command == "nodes":
                await list_nodes(naptha)   
            elif args.command == "agents":
                if not args.agent_name:
                    await list_agents(naptha)
                elif args.delete and len(args.agent_name.split()) == 1:
                    await naptha.hub.delete_agent(args.agent_name)
                elif len(args.agent_name.split()) == 1:
                    if hasattr(args, 'parameters') and args.parameters is not None:
                        params = shlex.split(args.parameters)
                        parsed_params = {}
                        for param in params:
                            key, value = param.split('=')
                            parsed_params[key] = value

                        required_parameters = ['description', 'url', 'type', 'version']
                        if not all(param in parsed_params for param in required_parameters):
                            print(f"Missing one or more of the following required parameters: {required_parameters}")
                            return
                            
                        agent_config = {
                            "id": f"agent:{args.agent_name}",
                            "name": args.agent_name,
                            "description": parsed_params['description'],
                            "author": naptha.hub.user_id,
                            "url": parsed_params['url'],
                            "type": parsed_params['type'],
                            "version": parsed_params['version'],
                        }
                        await create_agent(naptha, agent_config)
                else:
                    print("Invalid command.")
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
                
                if hasattr(args, 'worker_nodes') and args.worker_nodes is not None:
                    worker_nodes = args.worker_nodes.split(',')
                else:
                    worker_nodes = None
                
                await run(naptha, args.agent, user_id, parsed_params, worker_nodes, args.file)
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