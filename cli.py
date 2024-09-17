import argparse
import asyncio
from dotenv import load_dotenv
from naptha_sdk.client.naptha import Naptha
from naptha_sdk.user import get_public_key, generate_user
from naptha_sdk.schemas import ModuleRun
import os
import shlex
import time
import yaml
import json
from tabulate import tabulate
from textwrap import wrap

load_dotenv()

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

    # Print the first node to see its structure
    print("Sample node structure:")
    print(json.dumps(nodes[0], indent=2))

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

async def list_modules(naptha):
    modules = await naptha.hub.list_modules()
    
    if not modules:
        print("No modules found.")
        return

    headers = ["Name", "ID", "Type", "Version", "Author", "Description"]
    table_data = []

    for m in modules:
        # Wrap the description text
        wrapped_description = '\n'.join(wrap(m['description'], width=50))
        
        row = [
            m['name'],
            m['id'],
            m['type'],
            m['version'],
            m['author'],
            wrapped_description
        ]
        table_data.append(row)

    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    print(f"\nTotal modules: {len(modules)}")

async def create_module(naptha, module_config):
    print(f"Module Config: {module_config}")
    module = await naptha.hub.create_module(module_config)
    if isinstance(module, dict):
        print(f"Module created: {module}")
    elif isinstance(module, list):
        print(f"Module created: {module[0]}")

async def list_tasks(naptha):
    tasks = await naptha.hub.list_tasks()
    for task in tasks:
        print(task) 

async def list_rfps(naptha):
    rfps = await naptha.hub.list_rfps()
    for rfp in rfps:
        print(rfp) 

def generate_new_user():
    _, private_key = generate_user()
    print("PRIVATE_KEY: ", private_key)

async def run(
    naptha, 
    module_name, 
    parameters=None, 
    worker_nodes=None,
    yaml_file=None, 
):   
    if yaml_file and parameters:
        raise ValueError("Cannot pass both yaml_file and parameters")
    
    if yaml_file:
        parameters = load_yaml_to_dict(yaml_file)

    module_run_input = {
        'consumer_id': naptha.hub.user_id,
        "module_name": module_name,
        'worker_nodes': worker_nodes,
        "module_params": parameters,
    }
    
    print(f"Running module {module_name} with parameters: {module_run_input}")

    print("Checking user with public key: ", naptha.hub.public_key)
    user = await naptha.node.check_user(user_input={"public_key": naptha.hub.public_key})

    if user is not None:
        print("Found user...", user)
    else:
        print("No user found. Registering user...")
        user = await naptha.node.register_user(user_input=user)
        print(f"User registered: {user}.")

    print("Running...")
    module_run = await naptha.node.run_task(module_run_input)


    if isinstance(module_run, dict):
        module_run = ModuleRun(**module_run)

    print(f"Module Run ID: {module_run.id}")
    current_results_len = 0
    while True:
        module_run = await naptha.node.check_task(module_run)

        if isinstance(module_run, dict):
            module_run = ModuleRun(**module_run)

        output = f"{module_run.status} {module_run.module_type} {module_run.module_name}"
        if len(module_run.child_runs) > 0:
            output += f", task {len(module_run.child_runs)} {module_run.child_runs[-1].module_name} (node: {module_run.child_runs[-1].worker_nodes[0]})"
        print(output)

        if len(module_run.results) > current_results_len:
            print("Output: ", module_run.results[-1])
            current_results_len += 1

        if module_run.status == 'completed':
            break
        if module_run.status == 'error':
            break

        time.sleep(3)

    if module_run.status == 'completed':
        print(module_run.results)
    else:
        print(module_run.error_message)


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
    hub_url = os.getenv("HUB_URL")
    public_key = get_public_key(os.getenv("PRIVATE_KEY"))
    hub_username = os.getenv("HUB_USER")
    hub_password = os.getenv("HUB_PASS")
    node_url = os.getenv("NODE_URL", None)
    routing_url = os.getenv("ROUTING_URL", None)
    indirect_node_id = os.getenv("INDIRECT_NODE_ID", None)


    naptha = await Naptha(
        hub_url=hub_url,
        node_url=node_url,
        routing_url=routing_url,
        indirect_node_id=indirect_node_id,
        public_key=public_key,
        hub_username=hub_username,
        hub_password=hub_password,
    )

    parser = argparse.ArgumentParser(description="CLI with for Naptha")
    subparsers = parser.add_subparsers(title="commands", dest="command")

    # Node commands
    nodes_parser = subparsers.add_parser("nodes", help="List available nodes.")

    # Module commands
    modules_parser = subparsers.add_parser("modules", help="List available modules.")
    modules_parser.add_argument('module_name', nargs='?', help='Optional module name')
    modules_parser.add_argument("-p", '--parameters', type=str, help='Parameters in "key=value" format')
    modules_parser.add_argument('-d', '--delete', action='store_true', help='Delete a module')

    # Run command
    run_parser = subparsers.add_parser("run", help="Execute run command.")
    run_parser.add_argument("module", help="Select the module to run")
    run_parser.add_argument("-p", '--parameters', type=str, help='Parameters in "key=value" format')
    run_parser.add_argument("-n", "--worker_nodes", help="Worker nodes to take part in module runs.")
    run_parser.add_argument("-f", "--file", help="YAML file with module parameters")

    user_parser = subparsers.add_parser("user", help="Generate user.")

    # Read storage commands
    read_storage_parser = subparsers.add_parser("read_storage", help="Read from storage.")
    read_storage_parser.add_argument("-id", "--module_run_id", help="Module run ID to read from")
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

    
    # Parse arguments
    args = parser.parse_args()
    if args.command == "signup":
        success, token, user_id = await naptha.hub.loop_signup()
        if success:
            print(f"Signup successful. User ID: {user_id}")
        else:
            print("Signup failed.")
    elif args.command in ["nodes", "modules", "run", "read_storage", "write_storage"]:
        if not naptha.hub.is_authenticated:
            if not hub_username or not hub_password:
                print("Please set HUB_USER and HUB_PASS environment variables or sign up first (run naptha signup).")
                return
            success, _, _ = await naptha.hub.signin(hub_username, hub_password)
            if not success:
                print("Authentication failed. Please check your credentials.")
                return

        if args.command == "nodes":
            await list_nodes(naptha)   
        elif args.command == "modules":
            if not args.module_name:
                await list_modules(naptha)
            elif args.delete and len(args.module_name.split()) == 1:
                await naptha.hub.delete_module(args.module_name)
            elif len(args.module_name.split()) == 1:
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
                        
                    module_config = {
                        "id": f"module:{args.module_name}",
                        "name": args.module_name,
                        "description": parsed_params['description'],
                        "author": naptha.hub.user_id,
                        "url": parsed_params['url'],
                        "type": parsed_params['type'],
                        "version": parsed_params['version'],
                    }
                    await create_module(naptha, module_config)
            else:
                print("Invalid command.")
        elif args.command == "user":
            generate_new_user()  
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
            
            await run(naptha, args.module, parsed_params, worker_nodes, args.file)
        elif args.command == "read_storage":
            await read_storage(naptha, args.module_run_id, args.output_dir, args.ipfs)
        elif args.command == "write_storage":
            await write_storage(naptha, args.storage_input, args.ipfs, args.publish_to_ipns, args.update_ipns_name)
        elif args.command == "signup":
            success, token, user_id = await naptha.hub.loop_signup()
            if success:
                print(f"Signup successful. User ID: {user_id}")
            else:
                print("Signup failed.")
    else:
        parser.print_help()

def cli():
    asyncio.run(main())

if __name__ == "__main__":
    asyncio.run(main())