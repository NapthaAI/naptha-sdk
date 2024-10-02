from enum import Enum
from typing import Dict, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel

class AgentRunType(str, Enum):
    package = "package"
    docker = "docker"

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
    agent_name: str
    agent_run_type: AgentRunType
    consumer_id: str
    status: str = "pending"
    error: bool = False
    id: Optional[str] = None
    results: list[str] = []
    worker_nodes: Optional[list[str]] = None
    error_message: Optional[str] = None
    created_time: Optional[str] = None
    start_processing_time: Optional[str] = None
    completed_time: Optional[str] = None
    duration: Optional[float] = None
    agent_run_params: Optional[Union[Dict, DockerParams]] = None
    child_runs: List['AgentRun'] = []
    parent_runs: List['AgentRun'] = []
    input_schema_ipfs_hash: Optional[str] = None
    agent_source_url: Optional[str] = None
    agent_version: Optional[str] = None

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
            elif isinstance(value, AgentRunType):
                model_dict[key] = value.value
        for i, parent_run in enumerate(model_dict['parent_runs']):
            for key, value in parent_run.items():
                if isinstance(value, datetime):
                    model_dict['parent_runs'][i][key] = value.isoformat()
        for i, child_run in enumerate(model_dict['child_runs']):
            for key, value in child_run.items():
                if isinstance(value, datetime):
                    model_dict['child_runs'][i][key] = value.isoformat()
        return model_dict

class AgentRunInput(BaseModel):
    agent_name: str
    consumer_id: str
    worker_nodes: Optional[list[str]] = None
    agent_run_params: Optional[Union[Dict, DockerParams]] = None
    agent_run_type: Optional[AgentRunType] = None
    parent_runs: List['AgentRun'] = []
    agent_source_url: Optional[str] = None
    agent_version: Optional[str] = None

    def model_dict(self):
        model_dict = self.dict()
        for i, parent_run in enumerate(model_dict['parent_runs']):
            for key, value in parent_run.items():
                if isinstance(value, datetime):
                    model_dict['parent_runs'][i][key] = value.isoformat()
        return model_dict