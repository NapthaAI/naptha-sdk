import json
from pathlib import Path
from naptha_sdk.package_manager import load_persona
from naptha_sdk.schemas import AgentDeployment, EnvironmentDeployment, LLMConfig, OrchestratorDeployment

def load_llm_configs(llm_configs_path):
    with open(llm_configs_path, "r") as file:
        llm_configs = json.loads(file.read())
    return [LLMConfig(**config) for config in llm_configs]

def load_agent_deployments(agent_deployments_path, load_persona_data=True):
    with open(agent_deployments_path, "r") as file:
        agent_deployments = json.loads(file.read())

    for deployment in agent_deployments:
        # Load LLM config
        config_name = deployment["agent_config"]["llm_config"]["config_name"]
        config_path = f"{Path.cwd().name}/configs/llm_configs.json"
        llm_configs = load_llm_configs(config_path)
        llm_config = next(config for config in llm_configs if config.config_name == config_name)
        deployment["agent_config"]["llm_config"] = llm_config   

        if load_persona_data:
            persona_data = load_persona(deployment["agent_config"]["persona_module"]["url"])
            deployment["agent_config"]["persona_module"]["data"] = persona_data

    return [AgentDeployment(**deployment) for deployment in agent_deployments]

def load_orchestrator_deployments(orchestrator_deployments_path):
    with open(orchestrator_deployments_path, "r") as file:
        orchestrator_deployments = json.loads(file.read())
    return [OrchestratorDeployment(**deployment) for deployment in orchestrator_deployments]

def load_environment_deployments(environment_deployments_path):
    with open(environment_deployments_path, "r") as file:
        environment_deployments = json.loads(file.read())
    return [EnvironmentDeployment(**deployment) for deployment in environment_deployments]
