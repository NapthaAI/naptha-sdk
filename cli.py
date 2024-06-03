import argparse
import asyncio
from dotenv import load_dotenv
from naptha_sdk.client.naptha import Naptha
from naptha_sdk.user import get_public_key
import os
import shlex
import time
import yaml

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

async def list_nodes(hub):
    nodes = await hub.list_nodes()
    for node in nodes:
        print(node) 

async def list_modules(hub):
    modules = await hub.list_modules()
    for module in modules:
        print(module) 

async def list_tasks(hub):
    tasks = await hub.list_tasks()
    for task in tasks:
        print(task) 

async def list_rfps(hub):
    rfps = await hub.list_rfps()
    for rfp in rfps:
        print(rfp) 

async def run(
    naptha, 
    module_name, 
    parameters=None, 
    worker_nodes=None,
    yaml_file=None, 
    local=False, 
    docker=False
):   
    if yaml_file and parameters:
        raise ValueError("Cannot pass both yaml_file and parameters")
    
    if yaml_file:
        parameters = load_yaml_to_dict(yaml_file)

    module_run_input = {
        'consumer_id': naptha.user["id"],
        "module_name": module_name,
        'worker_nodes': worker_nodes,
    }

    if docker:
        module_run_input["docker_params"] = parameters
    else:
        module_run_input["module_params"] = parameters
    
    print(f"Running module {module_name} with parameters: {module_run_input}")

    def confirm():
        while True:
            response = input(f"You have {creds} credits. Running this module will cost {price} credits. Would you like to proceed? (y/n): ").strip().lower()
            if response == 'y':
                return True
            elif response == 'n':
                return False
            else:
                print("Invalid input. Please enter 'y' or 'n'.")

    if local == False:
        creds = naptha.services.show_credits()
        price = 0
        confirm = confirm()
        if not confirm:
            print("Exiting...")
            return None
    else:
        confirm = True

    print("Checking user...")
    user = await naptha.check_user(user_input=naptha.user)

    if user["is_registered"] == True:
        print("Found user...", user)
    elif user["is_registered"] == False:
        print("No user found. Registering user...")
        user = await naptha.register_user(user_input=user)
        print(f"User registered: {user}.")

    print("Running...")
    module_run = await naptha.run_task(module_run_input, local=local)

    print(f"Module Run ID: {module_run['id']}")
    current_results_len = 0
    while True:
        module_run = await naptha.check_task(module_run)

        output = f"{module_run['status']} {module_run['module_type']} {module_run['module_name']}"
        if len(module_run["child_runs"]) > 0:
            output += f", task {len(module_run['child_runs'])} {module_run['child_runs'][-1]['module_name']} (node: {module_run['child_runs'][-1]['worker_nodes'][0]})"
        print(output)

        if len(module_run['results']) > current_results_len:
            print("Output: ", module_run['results'][-1])
            current_results_len += 1

        if module_run['status'] == 'completed':
            break
        if module_run['status'] == 'error':
            break

        time.sleep(3)

    if module_run['status'] == 'completed':
        print(module_run['results'])
    else:
        print(module_run['error_message'])


async def read_storage(naptha, module_run_id, output_dir='files', local=False, ipfs=False):
    """Read from storage."""
    try:
        await naptha.read_storage(module_run_id.strip(), output_dir, local=local, ipfs=ipfs)
    except Exception as err:
        print(f"Error: {err}")


async def write_storage(naptha, storage_input, ipfs=False):
    """Write to storage."""
    try:
        response = await naptha.write_storage(storage_input, ipfs=ipfs)
        print(response)
    except Exception as err:
        print(f"Error: {err}")


async def main():
    public_key = get_public_key(os.getenv("PRIVATE_KEY"))
    user = {"public_key": public_key, "id": f"user:{public_key}"}
    hub_url = os.getenv("HUB_URL")
    hub_username = os.getenv("HUB_USER")
    hub_password = os.getenv("HUB_PASS")
    node_url = os.getenv("NODE_URL")

    naptha = await Naptha(
        user,
        hub_username, 
        hub_password, 
        hub_url,
        node_url,
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
    run_parser.add_argument("-l", "--local", help="Run locally", action="store_true")
    run_parser.add_argument("-d", "--docker", help="Run in docker", action="store_true")

    # Credits command
    credits_parser = subparsers.add_parser("credits", help="Show available credits.")
    services_parser = subparsers.add_parser("services", help="Show available services.")

    # Read storage commands
    read_storage_parser = subparsers.add_parser("read_storage", help="Read from storage.")
    read_storage_parser.add_argument("-id", "--module_run_id", help="Module run ID to read from")
    read_storage_parser.add_argument("-o", "--output_dir", default="files", help="Output directory to write to")
    read_storage_parser.add_argument("-l", "--local", help="Run locally", action="store_true")
    read_storage_parser.add_argument("--ipfs", help="Read from IPFS", action="store_true")

    # Write storage commands
    write_storage_parser = subparsers.add_parser("write_storage", help="Write to storage.")
    write_storage_parser.add_argument("-i", "--storage_input", help="Path to file or directory to write to storage")
    write_storage_parser.add_argument("--ipfs", help="Write to IPFS", action="store_true")

    # Parse arguments
    args = parser.parse_args()

    if args.command == "credits":
        creds(naptha)  
    elif args.command == "services":
        list_services(naptha)  
    elif args.command == "nodes":
        await list_nodes(hub)   
    elif args.command == "modules":
        await list_modules(hub)  
    elif args.command == "tasks":
        await list_tasks(hub)  
    elif args.command == "rfps":
        await list_rfps(hub)  
    elif args.command == "run":
        if hasattr(args, 'parameters') and args.parameters is not None:
            # Split the parameters string into key-value pairs
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
        await run(naptha, args.module, parsed_params, worker_nodes, args.file, args.local, args.docker)
    elif args.command == "read_storage":
        await read_storage(naptha, args.module_run_id, args.output_dir, args.local, args.ipfs)
    elif args.command == "write_storage":
        await write_storage(naptha, args.storage_input, args.ipfs)
    else:
        parser.print_help()

def cli():
    asyncio.run(main())

if __name__ == "__main__":
    asyncio.run(main())