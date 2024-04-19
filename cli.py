import argparse
import asyncio
from dotenv import load_dotenv
from naptha_sdk.hub import Hub
from naptha_sdk.services import Services
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

def creds(services):
    return services.show_credits()

def list_services(services):
    services = services.list_services()
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

async def run(hub, services, module_id, parameters=None, yaml_file=None, local=False):   
    if yaml_file:
        module_params = load_yaml_to_dict(yaml_file)
        print(f"Running module {module_id} with parameters: {module_params}")
    else:
        module_params = parameters        

    def confirm():
        while True:
            response = input(f"You have {creds} credits. Running this workflow will cost {price} credits. Would you like to proceed? (y/n): ").strip().lower()
            if response == 'y':
                return True
            elif response == 'n':
                return False
            else:
                print("Invalid input. Please enter 'y' or 'n'.")

    if local == False:
        creds = services.show_credits()
        price = 0
        confirm = confirm()
        if not confirm:
            print("Exiting...")
            return None
    else:
        confirm = True

    print("Running...")

    job = await services.run_task(task_input={
        'user_id': hub.user_id,
        "module_id": module_id,
        "module_params": module_params
    }, local=local)

    print(f"Job ID: {job['id']}")
    while True:
        j = await services.check_task({"id": job['id']})

        status = j['status']
        print(status)   

        if status == 'completed':
            break
        if status == 'error':
            break

        time.sleep(3)

    if j['status'] == 'completed':
        print(j['reply'])
    else:
        print(j['error_message'])


async def read_from_storage(services, job_id, output_dir='.'):
    """Read from storage."""
    try:
        await services.read_storage(job_id, output_dir)
    except Exception as err:
        print(f"Error: {err}")


async def write_from_storage(services, storage_input):
    """Write to storage."""
    try:
        response = await services.write_storage(storage_input)
        print(response)
    except Exception as err:
        print(f"Error: {err}")


async def main():
    hub_endpoint = os.getenv("HUB_ENDPOINT")
    username = os.getenv("HUB_USER")
    password = os.getenv("HUB_PASS")

    hub = await Hub(username, password, hub_endpoint)
    services = Services()

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
    run_parser.add_argument('parameters', type=str, help='Parameters in "key=value" format')
    run_parser.add_argument("-f", "--file", help="YAML file with module parameters")
    run_parser.add_argument("-l", "--local", help="Run locally", action="store_true")

    # Credits command
    credits_parser = subparsers.add_parser("credits", help="Show available credits.")
    services_parser = subparsers.add_parser("services", help="Show available services.")

    # Read storage commands
    read_storage_parser = subparsers.add_parser("read_storage", help="Read from storage.")
    read_storage_parser.add_argument("-id", "--job_id", help="Job ID to read from")
    read_storage_parser.add_argument("-o", "--output_dir", help="Output directory to write to")

    # Write storage commands
    write_storage_parser = subparsers.add_parser("write_storage", help="Write to storage.")
    write_storage_parser.add_argument("-i", "--storage_input", help="Comma separated list of files or directories to write to storage")

    # Parse arguments
    args = parser.parse_args()

    if args.command == "credits":
        creds(services)  
    elif args.command == "services":
        list_services(services)  
    elif args.command == "nodes":
        await list_nodes(hub)   
    elif args.command == "modules":
        await list_modules(hub)  
    elif args.command == "tasks":
        await list_tasks(hub)  
    elif args.command == "rfps":
        await list_rfps(hub)  
    elif args.command == "run":
        # Split the parameters string into key-value pairs
        params = shlex.split(args.parameters)
        parsed_params = {}
        for param in params:
            key, value = param.split('=')
            parsed_params[key] = value
        await run(hub, services, args.module, parsed_params, args.file, args.local)
    elif args.command == "read_storage":
        await read_from_storage(services, args.job_id, args.output_dir)
    elif args.command == "write_storage":
        await write_from_storage(services, args.storage_input.split(','))
    else:
        parser.print_help()

def cli():
    asyncio.run(main())

if __name__ == "__main__":
    asyncio.run(main())