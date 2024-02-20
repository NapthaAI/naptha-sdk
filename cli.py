import argparse
import asyncio
from naptha_sdk.hub import Hub
from naptha_sdk.coworker import Coworker
import time
import yaml

def load_yaml_to_dict(file_path):
    with open(file_path, 'r') as file:
        # Load the YAML content into a Python dictionary
        yaml_content = yaml.safe_load(file)
    return yaml_content


async def creds(hub):
    return await hub.get_credits()

async def purchases(hub):
    purchases = await hub.list_purchases()
    for purchase in purchases:
        print(purchase) 

async def coworkers(hub):
    coworkers = await hub.list_nodes()
    for coworker in coworkers:
        print(coworker) 

async def coops(hub):
    modules = await hub.list_modules()
    for module in modules:
        print(module) 

async def plans(hub, node):
    plans = await hub.list_plans({"node": node})
    plans = plans
    for plan in plans:
        print(plan) 
    return plans

async def run(hub, node_id, module_id, prompt=None, yaml_file=None):
    if yaml_file:
        module_params = load_yaml_to_dict(yaml_file)
        print(f"Running module {module_id} with parameters: {module_params}")
    else:
        module_params = None

    creds = await hub.get_credits()
    plans = await hub.list_plans({"node": f"{node_id}"})
    plans = plans[0]
    node = await hub.get_node(node_id)

    def confirm():
        while True:
            response = input(f"You have {creds} credits. Running this Co-Op will cost {plans['buy_it_now_price']} credits. Would you like to proceed? (y/n): ").strip().lower()
            if response == 'y':
                return True
            elif response == 'n':
                return False
            else:
                print("Invalid input. Please enter 'y' or 'n'.")

    if confirm():
        print("Running...")

        purchase = await hub.purchase(purchase={
            "me": hub.user_id,
            "auction": plans['id'], 
        })
        purchases = await hub.list_purchases(plan_id=purchase['out'])

        coworker = Coworker("buyer1", "buyer1pass", node['address'])

        if module_params:
            job = await coworker.run_task(task_input={
                'user_id': hub.user_id,
                'purchase_id': purchases['id'], 
                "module_id": module_id,
                "module_params": module_params
            })
        else:
            job = await coworker.run_task(task_input={
                'user_id': hub.user_id,
                'purchase_id': purchases['id'], 
                "module_id": module_id,
                "module_params": {"prompt": prompt}
            })

        while True:
            j = await coworker.check_task({"id": job['id']})

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

    else:
        print("Exiting...")



async def main():
    hub_endpoint = "ws://localhost:3003/rpc"
    hub = await Hub("buyer1", "buyer1pass", hub_endpoint)

    parser = argparse.ArgumentParser(description="CLI with 'auctions' and 'run' commands")
    subparsers = parser.add_subparsers(title="commands", dest="command")

    # Subparser for co-workers
    coworkers_parser = subparsers.add_parser("coworkers", help="List available Coworker Nodes.")

    # Subparser for co-ops
    coops_parser = subparsers.add_parser("coops", help="List available Co-Ops.")

    # Subparser for plans
    plans_parser = subparsers.add_parser("plans", help="List available plans.")
    plans_parser.add_argument("node", help="Select the node.")

    # Subparser for run
    run_parser = subparsers.add_parser("run", help="Execute run command.")
    run_parser.add_argument("node", help="Select the node to run on")
    run_parser.add_argument("module", help="Select the module to run")
    run_parser.add_argument("-p", "--prompt", help="Prompt message")
    run_parser.add_argument("-f", "--file", help="YAML file containing command parameters")
    
    # Subparser for credits
    credits_parser = subparsers.add_parser("credits", help="Show available credits.")

    # Subparser for purchases
    purchases_parser = subparsers.add_parser("purchases", help="Show previous purchases.")

    args = parser.parse_args()

    if args.command == "credits":
        await creds(hub)  
    elif args.command == "coworkers":
        await coworkers(hub)   
    elif args.command == "coops":
        await coops(hub)  
    elif args.command == "plans":
        await plans(hub, args.node)    
    elif args.command == "run":
        await run(hub, args.node, args.module, args.prompt, args.file)
    elif args.command == "purchases":
        await purchases(hub)   
    else:
        parser.print_help()

def cli():
    asyncio.run(main())

if __name__ == "__main__":
    asyncio.run(main())