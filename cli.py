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

load_dotenv()

def load_yaml_to_dict(file_path):
    with open(file_path, 'r') as file:
        # Load the YAML content into a Python dictionary
        yaml_content = yaml.safe_load(file)
    return yaml_content

def creds(naptha):
    return naptha.services.show_credits()

async def list_services(naptha):
    services = await naptha.hub.list_services()
    for service in services:
        print(service) 

async def list_nodes(naptha):
    nodes = await naptha.hub.list_nodes()
    for node in nodes:
        print(node) 

async def list_modules(naptha):
    modules = await naptha.hub.list_modules()
    for module in modules:
        print(module) 

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
        'consumer_id': naptha.user["id"],
        "module_name": module_name,
        'worker_nodes': worker_nodes,
        "module_params": parameters,
    }
    
    print(f"Running module {module_name} with parameters: {module_run_input}")

    print("Checking user...")
    user = await naptha.node.check_user(user_input=naptha.user)

    if user["is_registered"] == True:
        print("Found user...", user)
    elif user["is_registered"] == False:
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
    user, _ = generate_user(os.getenv("PRIVATE_KEY"))
    hub_url = os.getenv("HUB_URL")
    hub_username = os.getenv("HUB_USER")
    hub_password = os.getenv("HUB_PASS")
    hf_username = os.getenv("HF_USERNAME")
    hf_access_token = os.getenv("HF_ACCESS_TOKEN")
    node_url = os.getenv("NODE_URL", None)
    routing_url = os.getenv("ROUTING_URL", None)
    indirect_node_id = os.getenv("INDIRECT_NODE_ID", None)


    naptha = await Naptha(
        user=user,
        hub_username=hub_username,
        hub_password=hub_password,
        hf_username=hf_username,
        hf_access_token=hf_access_token,
        hub_url=hub_url,
        node_url=node_url,
        routing_url=routing_url,
        indirect_node_id=indirect_node_id,
    )

    parser = argparse.ArgumentParser(description="CLI with for Naptha")
    subparsers = parser.add_subparsers(title="commands", dest="command")

    # Node commands
    nodes_parser = subparsers.add_parser("nodes", help="List available nodes.")

    # Module commands
    modules_parser = subparsers.add_parser("modules", help="List available modules.")

    # Task commands
    tasks_parser = subparsers.add_parser("tasks", help="List available tasks.")

    # RFP commands
    rfps_parser = subparsers.add_parser("rfps", help="List available RFPs.")

    # Run command
    run_parser = subparsers.add_parser("run", help="Execute run command.")
    run_parser.add_argument("module", help="Select the module to run")
    run_parser.add_argument("-p", '--parameters', type=str, help='Parameters in "key=value" format')
    run_parser.add_argument("-n", "--worker_nodes", help="Worker nodes to take part in module runs.")
    run_parser.add_argument("-f", "--file", help="YAML file with module parameters")

    user_parser = subparsers.add_parser("user", help="Generate user.")

    # Credits command
    credits_parser = subparsers.add_parser("credits", help="Show available credits.")
    services_parser = subparsers.add_parser("services", help="Show available services.")

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

    # Parse arguments
    args = parser.parse_args()

    if args.command == "credits":
        creds(naptha)  
    elif args.command == "services":
        await list_services(naptha)  
    elif args.command == "nodes":
        await list_nodes(naptha)   
    elif args.command == "modules":
        await list_modules(naptha)  
    elif args.command == "tasks":
        await list_tasks(naptha)  
    elif args.command == "rfps":
        await list_rfps(naptha)  
    elif args.command == "user":
        generate_new_user()  
    elif args.command == "run":
        if hasattr(args, 'parameters') and args.parameters is not None:
            try:
                # First, try to parse as JSON
                parsed_params = json.loads(args.parameters)
            except json.JSONDecodeError:
                # If JSON parsing fails, fall back to the original method
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
    else:
        parser.print_help()

def cli():
    asyncio.run(main())

if __name__ == "__main__":
    asyncio.run(main())