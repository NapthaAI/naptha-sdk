import argparse
import asyncio
from dotenv import load_dotenv
# from naptha_sdk.hub import Hub
from naptha_sdk.payments import Hub
from naptha_sdk.coworker import Coworker
import time

load_dotenv()

def creds(hub):
    return hub.show_credits()

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

async def run(hub, node_id, module_id, prompt):
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

        job = await coworker.run_task(task_input={
            'user_id': hub.user_id,
            'purchase_id': purchases['id'], # "wins:7uihf6oem7b9bho9e216", 
            "module_id": module_id,
            "module_params": {"prompt": "tell me a joke"}
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
    hub_endpoint = "ws://localhost:3001/rpc"
    # hub_endpoint = "wss://hub.algoverai.link"
    # hub = await Hub("buyer1", "buyer1pass", hub_endpoint)
    hub = Hub()

    parser = argparse.ArgumentParser(description="CLI with 'auctions' and 'run' commands")
    subparsers = parser.add_subparsers(title="commands", dest="command")

    coworkers_parser = subparsers.add_parser("coworkers", help="List available Coworker Nodes.")
    coops_parser = subparsers.add_parser("coops", help="List available Co-Ops.")
    plans_parser.add_argument("node", help="Select the node.")
    run_parser = subparsers.add_parser("run", help="Execute run command.")
    run_parser.add_argument("node", help="Select the node to run on")
    run_parser.add_argument("module", help="Select the module to run")
    run_parser.add_argument("--prompt", help="Prompt message")
    credits_parser = subparsers.add_parser("credits", help="Show available credits.")
    services_parser = subparsers.add_parser("services", help="List available services.")
    subscription_parser = subparsers.add_parser("subscription", help="Order subscription.")

    args = parser.parse_args()

    if args.command == "credits":
        creds(hub)  
    elif args.command == "coworkers":
        await coworkers(hub)   
    elif args.command == "coops":
        await coops(hub)  
    elif args.command == "run":
        await run(hub, args.node, args.module, args.prompt)    
    elif args.command == "services":
        get_service_details(hub, "did:nv:a9ff0f7a6632c944d277af2c65e7d80e1579239695e1c4e2ff3fd278f4d0e1aa" )  
    elif args.command == "subscription":
        get_naptha_subscription()   
    else:
        parser.print_help()

def cli():
    asyncio.run(main())

if __name__ == "__main__":
    asyncio.run(main())