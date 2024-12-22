import json
from pathlib import Path
from naptha_sdk.package_manager import load_persona
from naptha_sdk.schemas import AgentDeployment, EnvironmentDeployment, LLMConfig, OrchestratorDeployment, ToolDeployment

def load_llm_configs(llm_configs_path):
    with open(llm_configs_path, "r") as file:
        llm_configs = json.loads(file.read())
    return [LLMConfig(**config) for config in llm_configs]

def load_agent_deployments(agent_deployments_path, load_persona_data=False, load_persona_schema=False):
    with open(agent_deployments_path, "r") as file:
        agent_deployments = json.loads(file.read())

    for deployment in agent_deployments:
        # Load LLM config
        config_name = deployment["agent_config"]["llm_config"]["config_name"]
        config_path = f"{Path.cwd().name}/configs/llm_configs.json"
        llm_configs = load_llm_configs(config_path)
        llm_config = next(config for config in llm_configs if config.config_name == config_name)
        deployment["agent_config"]["llm_config"] = llm_config   

        # Load tool deployments if they exist
        if "tool_deployments" in deployment and deployment["tool_deployments"]:
            tool_deployment_name = deployment["tool_deployments"][0]["name"]
            tool_deployment_path = f"{Path.cwd().name}/configs/tool_deployments.json"
            tool_deployments = load_tool_deployments(tool_deployment_path)
            tool_deployment = next(deployment for deployment in tool_deployments if deployment.name == tool_deployment_name)
            deployment["tool_deployments"][0] = tool_deployment

        if load_persona_data:
            persona_data, input_schema = load_persona(deployment["agent_config"]["persona_module"]["module_url"])
            deployment["agent_config"]["persona_module"]["data"] = persona_data
        if load_persona_schema:
            deployment["agent_config"]["persona_module"]["data"] = input_schema(**persona_data)

    return [AgentDeployment(**deployment) for deployment in agent_deployments]

def load_tool_deployments(tool_deployments_path):
    with open(tool_deployments_path, "r") as file:
        tool_deployments = json.loads(file.read())

    for deployment in tool_deployments:
        # Load LLM config if present
        if "tool_config" in deployment and "llm_config" in deployment["tool_config"]:
            config_name = deployment["tool_config"]["llm_config"]["config_name"]
            config_path = f"{Path.cwd().name}/configs/llm_configs.json"
            llm_configs = load_llm_configs(config_path)
            llm_config = next(config for config in llm_configs if config.config_name == config_name)
            deployment["tool_config"]["llm_config"] = llm_config

    return [ToolDeployment(**deployment) for deployment in tool_deployments]

def load_orchestrator_deployments(orchestrator_deployments_path):
    with open(orchestrator_deployments_path, "r") as file:
        orchestrator_deployments = json.loads(file.read())
    return [OrchestratorDeployment(**deployment) for deployment in orchestrator_deployments]

def load_environment_deployments(environment_deployments_path, config_schema=None):
    with open(environment_deployments_path, "r") as file:
        environment_deployments = json.loads(file.read())
    
    if config_schema:
        for deployment in environment_deployments:
            deployment["environment_config"] = config_schema

    return [EnvironmentDeployment(**deployment) for deployment in environment_deployments]
