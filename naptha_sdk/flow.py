from datetime import datetime
import functools
import json
from naptha_sdk.schemas import AgentRunInput
import os
import time
import traceback

  
class Flow:
    def __init__(self, name, user_id, worker_nodes, agent_run_params):
        self.name = name
        self.user_id = user_id
        self.worker_nodes = worker_nodes
        self.agent_run_params = agent_run_params

        flow_run_input = {
            "agent_name": self.name,
            "agent_run_params_type": "package",
            "consumer_id": self.user_id,
            "worker_nodes": [w.node_url for w in self.worker_nodes],
            "agent_run_params": self.agent_run_params,
        }
        self.flow_run = AgentRunInput(**flow_run_input)

