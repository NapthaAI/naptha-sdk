from enum import Enum
from typing import Dict, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel

class User(BaseModel):
    id: str

class LLMClientType(str, Enum):
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"
    ANTHROPIC = "anthropic"
    VLLM = "vllm"
    LITELLM = "litellm"
    OLLAMA = "ollama"

class LLMConfig(BaseModel):
    config_name: Optional[str] = "llm_config"
    client: LLMClientType
    model: Optional[str] = None
    max_tokens: int = 400
    temperature: float = 0
    api_base: Optional[str] = None

class AgentModuleType(str, Enum):
    package = "package"
    docker = "docker"

class AgentConfig(BaseModel):
    config_name: Optional[str] = "agent_config"
    llm_config: Optional[LLMConfig] = None
    persona_module: Optional[Union[Dict, BaseModel]] = None
    system_prompt: Optional[Union[Dict, BaseModel]] = None

class OrchestratorConfig(BaseModel):
    config_name: str
    max_rounds: str

class EnvironmentConfig(BaseModel):
    config_name: str
    environment_type: str

class AgentDeployment(BaseModel):
    name: str
    module: Dict
    worker_node_url: Optional[str] = "http://localhost:7001"
    agent_config: Optional[AgentConfig] = None

class OrchestratorDeployment(BaseModel):
    name: str
    module: str
    orchestrator_node_url: Optional[str] = "http://localhost:7001"
    orchestrator_config: Optional[OrchestratorConfig] = None

class EnvironmentDeployment(BaseModel):
    name: str
    environment_node_url: str
    environment_config: Optional[EnvironmentConfig] = None

class DockerParams(BaseModel):
    docker_image: str
    docker_command: Optional[str] = ""
    docker_num_gpus: Optional[int] = 0
    docker_env_vars: Optional[Dict] = None
    input_dir: Optional[str] = None
    input_ipfs_hash: Optional[str] = None
    docker_input_dir: Optional[str] = None
    docker_output_dir: Optional[str] = None
    save_location: str = "node"

    class Config:
        allow_mutation = True

    class Config:
        allow_mutation = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

    def model_dict(self):
        model_dict = self.dict()
        for key, value in model_dict.items():
            if isinstance(value, datetime):
                model_dict[key] = value.isoformat()
        return model_dict

class AgentRun(BaseModel):
    consumer_id: str
    inputs: Optional[Union[Dict, DockerParams]] = None
    agent_deployment: AgentDeployment
    orchestrator_runs: List['OrchestratorRun'] = []
    status: str = "pending"
    error: bool = False
    id: Optional[str] = None
    results: list[str] = []
    error_message: Optional[str] = None
    created_time: Optional[str] = None
    start_processing_time: Optional[str] = None
    completed_time: Optional[str] = None
    duration: Optional[float] = None
    input_schema_ipfs_hash: Optional[str] = None

    class Config:
        allow_mutation = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

    def model_dict(self):
        model_dict = self.dict()
        for key, value in model_dict.items():
            if isinstance(value, datetime):
                model_dict[key] = value.isoformat()
            elif isinstance(value, AgentModuleType):
                model_dict[key] = value.value
        for i, orchestrator_run in enumerate(model_dict['orchestrator_runs']):
            for key, value in orchestrator_run.items():
                if isinstance(value, datetime):
                    model_dict['orchestrator_runs'][i][key] = value.isoformat()
        return model_dict

class AgentRunInput(BaseModel):
    consumer_id: str
    inputs: Optional[Union[BaseModel, Dict, DockerParams]] = None
    agent_deployment: AgentDeployment
    orchestrator_runs: List['OrchestratorRun'] = []

    def model_dict(self):
        model_dict = self.dict()
        for i, orchestrator_run in enumerate(model_dict['orchestrator_runs']):
            for key, value in orchestrator_run.items():
                if isinstance(value, datetime):
                    model_dict['orchestrator_runs'][i][key] = value.isoformat()
        return model_dict
    
class OrchestratorRunInput(BaseModel):
    consumer_id: str
    inputs: Optional[Dict] = None
    orchestrator_deployment: OrchestratorDeployment
    agent_deployments: List[AgentDeployment]
    environment_deployment: Optional[EnvironmentDeployment] = None

class OrchestratorRun(BaseModel):
    consumer_id: str
    inputs: Optional[Dict] = None
    orchestrator_deployment: OrchestratorDeployment
    agent_deployments: List[AgentDeployment]
    environment_deployment: Optional[EnvironmentDeployment] = None
    status: str = "pending"
    error: bool = False
    id: Optional[str] = None
    results: list[str] = []
    error_message: Optional[str] = None
    created_time: Optional[str] = None
    start_processing_time: Optional[str] = None
    completed_time: Optional[str] = None
    duration: Optional[float] = None
    agent_runs: List['AgentRun'] = []
    input_schema_ipfs_hash: Optional[str] = None