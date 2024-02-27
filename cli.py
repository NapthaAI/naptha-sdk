import argparse
import asyncio
from naptha_sdk.hub import Hub
from naptha_sdk.coworker import Coworker
import time
import yaml
from pathlib import Path
import tarfile
import tempfile
import logging

HUB_ENDPOINT = "wss://hub.algoverai.link"

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger

logger = get_logger(__name__)

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

async def run(hub, node_id, module_id, prompt=None, yaml_file=None, save_path=None):
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
                logger.error("Invalid input. Please enter 'y' or 'n'.")

    if confirm():
        logger.info("Purchasing plan...")

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
            logger.info(f"Job status: {status}")  

            if status == 'completed':
                break
            if status == 'error':
                break

            time.sleep(3)

        if j['status'] == 'completed':
            logger.info(f"Job completed successfully! Job details: {job}")
            logger.info(f"Job output:\n{j['reply']}")
            return job['id']

        else:
            logger.error(f"Job failed. Job details: {job}")
            logger.error(f"Job output:\n{j['error_message']}")
            return job['id']

    else:
        logger.info("Exiting...")

async def write_to_storage(hub, node_id, storage_input):
    """Write to storage."""
    logger.info("Writing to storage...")
    node = await hub.get_node(node_id)
    coworker = Coworker("buyer1", "buyer1pass", node['address'])
    storage = await coworker.write_storage(storage_input)
    logger.info(f"Storage written: {storage}")
    return storage

async def read_from_storage(hub, node_id, storage_input, output_dir):
    """Read from storage."""
    logger.info("Reading from storage...")
    node = await hub.get_node(node_id)
    coworker = Coworker("buyer1", "buyer1pass", node['address'])
    response = await coworker.read_storage(storage_input)
    if response.status_code == 200:
        storage = response.content  # Here's the crucial change
        logger.info("Retrieved storage.")
        
        # Temporary file handling
        temp_file_name = None
        with tempfile.NamedTemporaryFile(delete=False, mode='wb') as tmp_file:
            tmp_file.write(storage)  # storage is now a bytes-like object
            temp_file_name = tmp_file.name
    
        # Ensure output directory exists
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
    
        # Extract the tar.gz file
        with tarfile.open(temp_file_name, "r:gz") as tar:
            tar.extractall(path=output_dir)
    
        logger.info(f"Extracted storage to {output_dir}.")
        
        # Cleanup temporary file
        Path(temp_file_name).unlink(missing_ok=True)
    
        return output_dir
    else:
        logger.error("Failed to retrieve storage.")

async def main():
    # hub_endpoint = "ws://54.82.77.109:3003/rpc"
    hub_endpoint = "wss://hub.algoverai.link"
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

    # subparser for write_storage
    write_storage_parser = subparsers.add_parser("write_storage", help="Write to storage.")
    write_storage_parser.add_argument("-n", "--node", help="Select the node to write to")
    write_storage_parser.add_argument("-i", "--storage_input", help="Comma separated list of files or directories to write to storage")

    # subparser for read_storage
    read_storage_parser = subparsers.add_parser("read_storage", help="Read from storage.")
    read_storage_parser.add_argument("-n", "--node", help="Select the node to read from")
    read_storage_parser.add_argument("-id", "--job_id", help="Job ID to read from")
    read_storage_parser.add_argument("-o", "--output_dir", help="Output directory to write to")

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
    elif args.command == "write_storage":
        await write_to_storage(hub, args.node, args.storage_input.split(','))   
    elif args.command == "read_storage":
        await read_from_storage(hub, args.node, args.job_id, args.output_dir)
    else:
        parser.print_help()

def cli():
    asyncio.run(main())

if __name__ == "__main__":
    asyncio.run(main())