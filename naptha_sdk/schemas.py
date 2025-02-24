from enum import Enum
from typing import Dict, List, Optional, Union, Any
from datetime import datetime
from pydantic import BaseModel, Field
from naptha_sdk.storage.schemas import StorageConfig

class User(BaseModel):
    id: str

class NodeServer(BaseModel):
    communication_protocol: str
    port: int
    node_id: str

class NodeConfig(BaseModel):
    id: str
    owner: str
    public_key: str
    ip: str = Field(default="localhost")
    user_communication_protocol: str = Field(default="http")
    node_communication_protocol: str = Field(default="ws")
    user_communication_port: int = Field(default=7001)
    num_node_communication_servers: int = Field(default=1)
    provider_types: List[str] = Field(default=["models", "storage", "modules"])
    servers: List[NodeServer]
    models: List[str]
    docker_jobs: bool
    ports: Optional[List[int]] = None
    routing_type: Optional[str] = Field(default="direct")
    routing_url: Optional[str] = Field(default=None)
    num_gpus: Optional[int] = Field(default=None)
    arch: Optional[str] = Field(default=None)
    os: Optional[str] = Field(default=None)
    ram: Optional[int] = Field(default=None)
    vram: Optional[int] = Field(default=None)

class NodeConfigUser(BaseModel):
    ip: str
    user_communication_port: Optional[int] = None
    user_communication_protocol: Optional[str] = None

class LLMClientType(str, Enum):
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"
    ANTHROPIC = "anthropic"
    VLLM = "vllm"
    LITELLM = "litellm"
    OLLAMA = "ollama"
    STABILITY = "stability"

class EmbeddingModelOptions(BaseModel):
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None
    separators: Optional[List[str]] = None
    embedding_dim: Optional[int] = None

class LLMConfig(BaseModel):
    config_name: Optional[str] = "llm_config"
    client: Optional[LLMClientType] = None
    model: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    api_base: Optional[str] = None
    options: Optional[EmbeddingModelOptions] = None

class AgentConfig(BaseModel):
    config_name: Optional[str] = "agent_config"
    llm_config: Optional[LLMConfig] = None
    persona_module: Optional[Union[Dict, BaseModel]] = None
    system_prompt: Optional[Union[Dict, BaseModel]] = None

class ToolConfig(BaseModel):
    config_name: Optional[str] = None
    llm_config: Optional[LLMConfig] = None

class OrchestratorConfig(BaseModel):
    config_name: Optional[str] = "orchestrator_config"
    llm_config: Optional[LLMConfig] = None
    max_rounds: Optional[int] = 5

class EnvironmentConfig(BaseModel):
    config_name: Optional[str] = "environment_config"
    llm_config: Optional[LLMConfig] = None
    environment_type: Optional[str] = None
    storage_config: Optional[StorageConfig] = None

    def model_dict(self):
        if isinstance(self.storage_config, StorageConfig):
            self.storage_config = self.storage_config.model_dict()
        model_dict = self.dict()
        model_dict['storage_config'] = self.storage_config
        return model_dict

class KBConfig(BaseModel):
    config_name: Optional[str] = None
    llm_config: Optional[LLMConfig] = None
    storage_config: Optional[StorageConfig] = None

    def model_dict(self):
        model_dict = self.dict()
        if isinstance(self.storage_config, StorageConfig):
            self.storage_config = self.storage_config.model_dict()
        model_dict['storage_config'] = self.storage_config
        return model_dict

class MemoryConfig(BaseModel):
    config_name: Optional[str] = None
    llm_config: Optional[LLMConfig] = None
    storage_config: Optional[StorageConfig] = None

    def model_dict(self):
        if isinstance(self.storage_config, StorageConfig):
            self.storage_config = self.storage_config.model_dict()
        model_dict = self.dict()
        model_dict['storage_config'] = self.storage_config
        return model_dict

class DataGenerationConfig(BaseModel):
    save_outputs: Optional[bool] = None
    save_outputs_location: Optional[str] = None
    save_outputs_path: Optional[str] = None
    save_inputs: Optional[bool] = None
    save_inputs_location: Optional[str] = None
    default_filename: Optional[str] = None

class ToolDeployment(BaseModel):
    node: Union[NodeConfig, NodeConfigUser, Dict]
    name: Optional[str] = None
    module: Optional[Dict] = None
    config: Optional[ToolConfig] = None
    data_generation_config: Optional[DataGenerationConfig] = None

class KBDeployment(BaseModel):
    node: Union[NodeConfig, NodeConfigUser, Dict]
    name: Optional[str] = None
    module: Optional[Dict] = None
    config: Optional[KBConfig] = None

    def model_dict(self):
        model_dict = self.dict()
        if isinstance(self.config, KBConfig):
            model_dict['config'] = self.config.model_dict()
        return model_dict

class MemoryDeployment(BaseModel):
    node: Union[NodeConfig, NodeConfigUser, Dict]
    name: Optional[str] = None
    module: Optional[Dict] = None
    config: Optional[MemoryConfig] = None

    def model_dict(self):
        model_dict = self.dict()
        if isinstance(self.config, MemoryConfig):
            model_dict['config'] = self.config.model_dict()
        return model_dict

class EnvironmentDeployment(BaseModel):
    node: Union[NodeConfig, NodeConfigUser, Dict]
    name: Optional[str] = None
    module: Optional[Dict] = None
    config: Optional[EnvironmentConfig] = None

class AgentDeployment(BaseModel):
    node: Union[NodeConfig, NodeConfigUser, Dict]
    name: Optional[str] = None
    module: Optional[Dict] = None
    config: Optional[AgentConfig] = None
    data_generation_config: Optional[DataGenerationConfig] = None
    tool_deployments: Optional[List[ToolDeployment]] = None
    environment_deployments: Optional[List[EnvironmentDeployment]] = None
    kb_deployments: Optional[List[KBDeployment]] = None
    memory_deployments: Optional[List[MemoryDeployment]] = None

class OrchestratorDeployment(BaseModel):
    node: Union[NodeConfig, NodeConfigUser, Dict]
    name: Optional[str] = None
    module: Optional[Dict] = None
    config: Optional[OrchestratorConfig] = None
    agent_deployments: Optional[List[AgentDeployment]] = None
    environment_deployments: Optional[List[EnvironmentDeployment]] = None
    kb_deployments: Optional[List[KBDeployment]] = None
    memory_deployments: Optional[List[MemoryDeployment]] = None

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

    def model_dict(self):
        model_dict = self.dict()
        for key, value in model_dict.items():
            if isinstance(value, datetime):
                model_dict[key] = value.isoformat()
        return model_dict

class AgentRun(BaseModel):
    consumer_id: str
    inputs: Optional[Union[Dict, BaseModel, DockerParams]] = None
    deployment: AgentDeployment
    tool_deployments: Optional[List[ToolDeployment]] = None
    environment_deployments: Optional[List[EnvironmentDeployment]] = None
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
    signature: str

    def model_dict(self):
        model_dict = self.dict()
        for key, value in model_dict.items():
            if isinstance(value, datetime):
                model_dict[key] = value.isoformat()
        for i, orchestrator_run in enumerate(model_dict['orchestrator_runs']):
            for key, value in orchestrator_run.items():
                if isinstance(value, datetime):
                    model_dict['orchestrator_runs'][i][key] = value.isoformat()
        return model_dict

class AgentRunInput(BaseModel):
    consumer_id: str
    inputs: Optional[Union[Dict, BaseModel, DockerParams]] = None
    deployment: AgentDeployment
    tool_deployments: Optional[List[ToolDeployment]] = None
    environment_deployments: Optional[List[EnvironmentDeployment]] = None
    kb_deployment: Optional[KBDeployment] = None
    orchestrator_runs: List['OrchestratorRun'] = []
    signature: str

    def model_dict(self):
        model_dict = self.dict()
        if isinstance(self.deployment.config, BaseModel):
            config = self.deployment.config.model_dump()
            model_dict['deployment']['config'] = config
        return model_dict


class ToolRunInput(BaseModel):
    consumer_id: str
    inputs: Optional[Union[Dict, BaseModel, DockerParams]] = None
    deployment: ToolDeployment
    agent_run: Optional[AgentRun] = None
    signature: str

    def model_dict(self):
        if isinstance(self.inputs, BaseModel):
            self.inputs = self.inputs.model_dump()
        model_dict = self.dict()
        model_dict['inputs'] = self.inputs
        return model_dict

class ToolRun(BaseModel):
    consumer_id: str
    inputs: Optional[Union[Dict, BaseModel, DockerParams]] = None
    deployment: ToolDeployment
    agent_run: Optional[AgentRun] = None
    status: str = "pending"
    error: bool = False
    id: Optional[str] = None
    results: list[str] = []
    error_message: Optional[str] = None
    created_time: Optional[str] = None
    start_processing_time: Optional[str] = None
    completed_time: Optional[str] = None
    duration: Optional[float] = None
    signature: str

class OrchestratorRunInput(BaseModel):
    consumer_id: str
    inputs: Optional[Union[Dict, BaseModel, DockerParams]] = None
    deployment: OrchestratorDeployment
    signature: str

    def model_dict(self):
        model_dict = self.dict()
        return model_dict

class OrchestratorRun(BaseModel):
    consumer_id: str
    inputs: Optional[Union[Dict, BaseModel, DockerParams]] = None
    deployment: OrchestratorDeployment
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
    signature: str

class EnvironmentRunInput(BaseModel):
    consumer_id: str
    inputs: Optional[Union[Dict, BaseModel, DockerParams]] = None
    deployment: EnvironmentDeployment
    orchestrator_runs: List['OrchestratorRun'] = []
    signature: str

    def model_dict(self):
        model_dict = self.dict()
        return model_dict

class EnvironmentRun(BaseModel):
    consumer_id: str
    inputs: Optional[Union[Dict, BaseModel, DockerParams]] = None
    deployment: EnvironmentDeployment
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
    signature: str

class KBRunInput(BaseModel):
    consumer_id: str
    inputs: Optional[Union[Dict, BaseModel, DockerParams]] = None
    deployment: KBDeployment
    orchestrator_runs: List['OrchestratorRun'] = []
    signature: str

    def model_dict(self):
        model_dict = self.dict()
        if isinstance(self.deployment, KBDeployment):
            model_dict['deployment'] = self.deployment.model_dict()
        return model_dict

class KBRun(BaseModel):
    consumer_id: str
    inputs: Optional[Union[Dict, BaseModel, DockerParams]] = None
    deployment: KBDeployment
    orchestrator_runs: List['OrchestratorRun'] = []
    status: str = "pending"
    error: bool = False
    id: Optional[str] = None
    results: list[Optional[str]] = []
    error_message: Optional[str] = None
    created_time: Optional[str] = None
    start_processing_time: Optional[str] = None
    completed_time: Optional[str] = None
    duration: Optional[float] = None
    signature: str

class MemoryRunInput(BaseModel):
    consumer_id: str
    inputs: Optional[Union[Dict, BaseModel, DockerParams]] = None
    deployment: MemoryDeployment
    orchestrator_runs: List['OrchestratorRun'] = []
    signature: str

    def model_dict(self):
        model_dict = self.dict()
        if isinstance(self.deployment, MemoryDeployment):
            model_dict['deployment'] = self.deployment.model_dict()
        return model_dict

class MemoryRun(BaseModel):
    consumer_id: str
    inputs: Optional[Union[Dict, BaseModel, DockerParams]] = None
    deployment: MemoryDeployment
    orchestrator_runs: List['OrchestratorRun'] = []
    status: str = "pending"
    error: bool = False
    id: Optional[str] = None
    results: list[Optional[str]] = []
    error_message: Optional[str] = None
    created_time: Optional[str] = None
    start_processing_time: Optional[str] = None
    completed_time: Optional[str] = None
    duration: Optional[float] = None
    signature: str

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    stop: Optional[List[str]] = None
    stream: Optional[bool] = None
    stream_options: Optional[dict] = None
    n: Optional[int] = None
    response_format: Optional[dict] = None
    seed: Optional[int] = None
    tools: Optional[List] = None
    tool_choice: Optional[str] = None
    parallel_tool_calls: Optional[bool] = None

class Choices(BaseModel):
    message: ChatMessage
    finish_reason: str
    index: int

class ModelResponse(BaseModel):
    id: str
    choices: List[Choices]
    created: int
    model: str
    object: str

class SecretInput(BaseModel):
    user_id: str
    secret_value: str
    key_name: str

    def model_dict(self):
        model_dict = self.model_dump()
        return model_dict