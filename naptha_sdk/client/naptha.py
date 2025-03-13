import asyncio
from dotenv import load_dotenv
import inspect
import json
import os
import time
from pathlib import Path

import tomlkit
from naptha_sdk.client.hub import Hub
from naptha_sdk.client.node import UserClient
from naptha_sdk.configs import setup_module_deployment
from naptha_sdk.inference import InferenceClient
from naptha_sdk.module_manager import AGENT_DIR, add_files_to_package, add_dependencies_to_pyproject, git_add_commit, \
    init_agent_package, publish_ipfs_package, render_agent_code, write_code_to_package
from naptha_sdk.schemas import User
from naptha_sdk.scrape import scrape_init, scrape_func, scrape_func_params
from naptha_sdk.user import get_public_key
from naptha_sdk.utils import get_logger, url_to_node

logger = get_logger(__name__)

load_dotenv(override=True)

class Naptha:
    """The entry point into Naptha."""

    def __init__(self):
        self.public_key = get_public_key(os.getenv("PRIVATE_KEY")) if os.getenv("PRIVATE_KEY") else None
        self.user = User(id=f"user:{self.public_key}")
        self.hub_username = os.getenv("HUB_USERNAME", None)
        self.hub_url = os.getenv("HUB_URL", None)

        node_url = os.getenv("NODE_URL")

        if node_url is None:
            raise ValueError("NODE_URL is not set. Make sure your project has a .env file with a NODE_URL variable.")

        self.node = UserClient(url_to_node(node_url))
        self.inference_client = InferenceClient(url_to_node(node_url))
        self.hub = Hub(self.hub_url, self.public_key)  

    async def __aenter__(self):
        """Async enter method for context manager"""
        await self.hub.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async exit method for context manager"""
        await self.hub.close()


    async def create_agent(self, name):
        async with self.hub:
            _, _, user_id = await self.hub.signin(self.hub_username, os.getenv("HUB_PASSWORD"))
            agent_config = {
                "id": f"agent:{name}",
                "name": name,
                "description": name,
                "author": self.hub.user_id,
                "module_url": "None",
                "module_type": "agent",
                "module_version": "v0.1",
                "execution_type": "package",
                "module_entrypoint": "run.py",
                "parameters": "",
            }
            logger.info(f"Registering Agent {agent_config}")
            agent = await self.hub.create_or_update_module("agent", agent_config)
            if agent:
                logger.info(f"Agent {name} created successfully")
            else:
                logger.error(f"Failed to create agent {name}")

    async def publish_modules(self, decorator = False, register = None, subdeployments = False):
        logger.info(f"Publishing Agent Packages...")
        start_time = time.time()

        if not decorator:
            module_path = Path.cwd()
            deployment_path = module_path / module_path.name / "configs" / "deployment.json"
            with open(deployment_path, "r", encoding="utf-8") as f:
                deployment = json.load(f)
            module = deployment[0]["module"]
            if "module_type" not in module:
                module["module_type"] = "agent"
            modules = [module]
            if subdeployments:
                deployment = await setup_module_deployment(module['module_type'], deployment_path)
                for module_type in ['agent', 'kb', 'tool', 'environment']:
                    subdeployment = module_type + '_deployments'
                    if hasattr(deployment, subdeployment) and getattr(deployment, subdeployment):
                        for submodule in getattr(deployment, subdeployment):
                            modules.append(submodule.module)
        else:
            path = Path.cwd() / AGENT_DIR
            dir_items = [item.name for item in path.iterdir() if item.is_dir()]
            modules = []
            for mod_item in dir_items:
                git_add_commit(mod_item)
                mod_data = {
                    "name": mod_item,
                    "description": mod_item,
                    "parameters": "",
                    "module_type": "agent",
                    "module_url": "None",
                    "module_version": "v0.1",
                    "module_entrypoint": "run.py",
                    "execution_type": "package"
                }
                modules.append(mod_data)

        for module in modules:
            if "module_url" in module and module['module_url'] != "None":
                module_url = module['module_url']
            # For decorator=False, only the main module should not have a module_url
            else:
                # If register is a string, use it as the URL
                if isinstance(register, str):
                    module_url = register
                    logger.info(f"Using provided URL for {module['module_type']} {module['name']}: {module_url}")
                # Otherwise, publish to IPFS
                else:
                    _, response = await publish_ipfs_package(module["name"], decorator)
                    module_url = f"ipfs://{response['ipfs_hash']}"
                    logger.info(f"Storing {module['name']} on IPFS")
                    logger.info(f"Module URL: {module_url}")
                    logger.info(f"IPFS Hash: {response['ipfs_hash']}. You can download it from http://ipfs-gateway.naptha.work/ipfs/{response['ipfs_hash']}")

            if register:
                # Register module with hub
                async with self.hub:
                    _, _, user_id = await self.hub.signin(self.hub_username, os.getenv("HUB_PASSWORD"))
                    module_config = {
                        "id": f"{module['module_type']}:{module['name']}",
                        "name": module["name"],
                        "description": module.get("description", "No description provided"),
                        "parameters": module.get("parameters", ""),
                        "author": self.hub.user_id,
                        "module_url": module_url,
                        "module_type": module["module_type"],
                        "module_version": module.get("module_version", "v0.1"),
                        "module_entrypoint": module.get("module_entrypoint", "run.py"),
                        "execution_type": module.get("execution_type", "package"),
                    }
                    logger.info(f"Registering {module['module_type']} {module['name']} on Naptha Hub {module_config}")
                    module = await self.hub.create_or_update_module(module['module_type'], module_config)

        end_time = time.time()
        total_time = end_time - start_time
        logger.info(f"Total time taken to publish {len(modules)} modules: {total_time:.2f} seconds")

    def build(self):
        asyncio.run(self.build_agents())

    async def connect_publish(self):
        await self.hub.connect()
        await self.hub.signin(os.getenv("HUB_USERNAME"), os.getenv("HUB_PASSWORD"))
        await self.publish_agents()
        await self.hub.close()

    async def connect_user_secret(self, key_name):
        await self.hub.connect()
        await self.hub.signin(os.getenv("HUB_USERNAME"), os.getenv("HUB_PASSWORD"))
        result = await self.hub.get_user_secret(key_name)
        await self.hub.close()

        return result

    def publish(self):
        asyncio.run(self.connect_publish())

    def get_user_secret(self, key_name: str) -> str:
        result = asyncio.run(self.connect_user_secret(key_name))
        return result[0]['secret_value'] if len(result) > 0 else []


def agent(name):
    def decorator(func):
        frame = inspect.currentframe()
        package_dependencies = {}
        caller_frame = frame.f_back
        instantiation_file = caller_frame.f_code.co_filename
        variables = scrape_init(instantiation_file)
        
        # Parse pyproject.toml to get package dependencies
        pyproject_path = Path(os.path.join(Path.cwd() / AGENT_DIR, name, "pyproject.toml"))
        if pyproject_path.exists():
            with open(pyproject_path, "r", encoding="utf-8") as f:
                toml_data = tomlkit.load(f)
            if "tool" in toml_data and "poetry" in toml_data["tool"] and "dependencies" in toml_data["tool"]["poetry"]:
                deps = toml_data["tool"]["poetry"]["dependencies"]
                for pkg_name, version in deps.items():
                    if pkg_name == "python":
                        package_dependencies["python_version"] = str(version)
                    else:
                        package_dependencies[pkg_name] = str(version)
        else:
            logger.warning(f"pyproject.toml not found at {pyproject_path}")        
        
        params = scrape_func_params(func)
        agent_code, obj_name, local_modules, selective_import_modules, standard_import_modules, variable_modules, union_modules = scrape_func(func, variables)
                
        # Collect all imports for framework detection
        all_imports = (
            [mod["module"] for mod in selective_import_modules if "module" in mod]
            + [mod["name"] for mod in standard_import_modules]
        )
        agent_code = render_agent_code(name, agent_code, obj_name, local_modules, selective_import_modules, standard_import_modules, variable_modules, union_modules, params,all_imports,package_dependencies,)
        init_agent_package(name)
        write_code_to_package(name, agent_code)
        add_dependencies_to_pyproject(name, selective_import_modules + standard_import_modules)
        add_files_to_package(name, params, os.getenv("HUB_USERNAME"))

        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(Naptha().create_agent(name))
        else:
            loop.run_until_complete(Naptha().create_agent(name))

        return func
    return decorator

class Agent:
    def __init__(self, 
        name, 
        fn, 
        agent_node_url, 
    ):
        self.name = name
        self.fn = fn
        self.agent_node_url = agent_node_url
        self.repo_id = name