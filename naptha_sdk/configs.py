import json
import os
from pathlib import Path
from naptha_sdk.client.hub import list_nodes
from naptha_sdk.client.node import UserClient
from naptha_sdk.module_manager import load_persona
from naptha_sdk.schemas import AgentDeployment, EnvironmentDeployment, LLMConfig, OrchestratorDeployment, ToolDeployment, KBDeployment, KBConfig, AgentConfig, EnvironmentConfig, ToolConfig, OrchestratorConfig, NodeConfig
from naptha_sdk.utils import url_to_node

def load_llm_configs(llm_configs_path):
    with open(llm_configs_path, "r") as file:
        llm_configs = json.loads(file.read())
    return [LLMConfig(**config) for config in llm_configs]

async def load_node_metadata(deployment, node_url, is_subdeployment):
    if node_url is None:
        node_url = os.getenv("NODE_URL")
        if node_url is None:
            raise Exception("Node URL is required. Please make sure you've added NODE_URL=<node_url> to your .env file.")

    print(f"Loading node metadata for {deployment['node']['ip']}")
    if not is_subdeployment:
        deployment["node"] = url_to_node(node_url)
    else:
        deployment["node"] = await list_nodes(deployment["node"]["ip"])
        deployment["node"] = NodeConfig(**deployment["node"])
    print(f"Node metadata loaded {deployment['node']}")
    return deployment

async def check_register_user(deployment, user_id=None):
    node = UserClient(deployment["node"])
    user = await node.check_user(user_input={"public_key": user_id.split(":")[-1]})

    if user['is_registered'] == True:
        print("Found user...", user)
    else:
        print("No user found. Registering user...")
        user = await node.register_user(user_input=user)
        print(f"User registered: {user}.")

async def load_module_config_data(module_type, deployment, load_persona_data=False):

    config_map = {
        "agent": AgentConfig,
        "environment": EnvironmentConfig,
        "tool": ToolConfig,
        "orchestrator": OrchestratorConfig,
        "kb": KBConfig
    }

    if "llm_config" in deployment["config"] and deployment["config"]["llm_config"] is not None:
        config_name = deployment["config"]["llm_config"]["config_name"]
        config_path = f"{Path.cwd().name}/configs/llm_configs.json"
        llm_configs = load_llm_configs(config_path)
        llm_config = next(config for config in llm_configs if config.config_name == config_name)
        deployment["config"]["llm_config"] = llm_config
    if load_persona_data:
        persona_data = await load_persona(deployment["config"]["persona_module"])
        deployment["config"]["system_prompt"]["persona"] = persona_data

    deployment["config"] = config_map[module_type](**deployment["config"])

    return deployment

async def load_subdeployments(deployment, node_url=None, user_id=None):

    configs_path = Path(f"{Path.cwd().name}/configs")

    if "agent_deployments" in deployment and deployment["agent_deployments"]:
        # Update defaults with non-None values from input
        agent_deployments = []
        for i, agent_deployment in enumerate(deployment["agent_deployments"]):
            deployment_name = deployment["agent_deployments"][i]["name"]
            agent_deployment = await setup_module_deployment("agent", configs_path / "agent_deployments.json", node_url, user_id, deployment_name, is_subdeployment=True)
            agent_deployments.append(agent_deployment)
        deployment["agent_deployments"] = agent_deployments
    if "tool_deployments" in deployment and deployment["tool_deployments"]:
        tool_deployments = []
        for i, tool_deployment in enumerate(deployment["tool_deployments"]):
            deployment_name = deployment["tool_deployments"][i]["name"]
            tool_deployment = await setup_module_deployment("tool", configs_path / "tool_deployments.json", node_url, user_id, deployment_name, is_subdeployment=True)
            tool_deployments.append(tool_deployment)
        deployment["tool_deployments"] = tool_deployments
    if "environment_deployments" in deployment and deployment["environment_deployments"]:
        environment_deployments = []
        for i, environment_deployment in enumerate(deployment["environment_deployments"]):
            deployment_name = deployment["environment_deployments"][i]["name"]
            environment_deployment = await setup_module_deployment("environment", configs_path / "environment_deployments.json", node_url, user_id, deployment_name, is_subdeployment=True)
            environment_deployments.append(environment_deployment)
        deployment["environment_deployments"] = environment_deployments
    if "kb_deployments" in deployment and deployment["kb_deployments"]:
        kb_deployments = []
        for i, kb_deployment in enumerate(deployment["kb_deployments"]):
            deployment_name = deployment["kb_deployments"][i]["name"]
            kb_deployment = await setup_module_deployment("kb", configs_path / "kb_deployments.json", node_url, user_id, deployment_name, is_subdeployment=True)
            kb_deployments.append(kb_deployment)
        deployment["kb_deployments"] = kb_deployments
    print(f"Subdeployments loaded {deployment}")
    return deployment

async def setup_module_deployment(module_type: str, deployment_path: str, node_url: str = None, user_id: str = None, deployment_name: str = None, load_persona_data=False, is_subdeployment: bool = False):

    # Map deployment types to their corresponding classes
    deployment_map = {
        "agent": AgentDeployment,
        "tool": ToolDeployment,
        "environment": EnvironmentDeployment,
        "kb": KBDeployment,
        "orchestrator": OrchestratorDeployment
    }

    # Load default deployment config from module
    with open(deployment_path, "r") as file:
        deployment = json.loads(file.read())

    if deployment_name is None:
        deployment = deployment[0]
    else:
        # Get the first deployment with matching name
        deployment = next((d for d in deployment if d["name"] == deployment_name), None)
        if deployment is None:
            raise ValueError(f"No deployment found with name {deployment_name}")

    if node_url is not None:
        deployment = await load_node_metadata(deployment, node_url, is_subdeployment)
    if user_id is not None:
        await check_register_user(deployment, user_id)
    deployment = await load_module_config_data(module_type, deployment, load_persona_data)
    deployment = await load_subdeployments(deployment, node_url, user_id)
    return deployment_map[module_type](**deployment)