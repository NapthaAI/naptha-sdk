import argparse
import asyncio
from dotenv import load_dotenv
from naptha_sdk.hub import Hub
from naptha_sdk.services import Services
import os
import time

load_dotenv()

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

async def run(hub, services, module_id, prompt, local):

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
        "module_params": {"prompt": prompt}
    }, local=local)

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



async def main():
    hub_endpoint = os.getenv("HUB_ENDPOINT")
    username = os.getenv("HUB_USER")
    password = os.getenv("HUB_PASS")

    hub = await Hub(username, password, hub_endpoint)
    services = Services()

    parser = argparse.ArgumentParser(description="CLI with for Naptha")
    subparsers = parser.add_subparsers(title="commands", dest="command")

    nodes_parser = subparsers.add_parser("nodes", help="List available nodes.")
    modules_parser = subparsers.add_parser("modules", help="List available modules.")
    tasks_parser = subparsers.add_parser("tasks", help="List available tasks.")
    rfps_parser = subparsers.add_parser("rfps", help="List available RFPs.")
    orgs_parser = subparsers.add_parser("orgs", help="List current organizations.")
    run_parser = subparsers.add_parser("run", help="Execute run command.")
    run_parser.add_argument("module", help="Select the module to run")
    run_parser.add_argument("--prompt", help="Prompt message")
    run_parser.add_argument("--local", action='store_true', help="Whether to run on local node.")
    credits_parser = subparsers.add_parser("credits", help="Show available credits.")
    services_parser = subparsers.add_parser("services", help="Show available services.")

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
        await run(hub, services, args.module, args.prompt, args.local)    
    else:
        parser.print_help()

def cli():
    asyncio.run(main())

if __name__ == "__main__":
    asyncio.run(main())