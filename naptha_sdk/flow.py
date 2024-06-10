from datetime import datetime
import functools
import json
from naptha_sdk.schemas import ModuleRunInput
import os
import time
import traceback

  
class Flow:
    def __init__(self, name, user_id, worker_nodes, module_params):
        self.name = name
        self.user_id = user_id
        self.worker_nodes = worker_nodes
        self.module_params = module_params

        flow_run_input = {
            "module_name": self.name,
            "module_type": "template",
            "consumer_id": self.user_id,
            "worker_nodes": [w.node_url for w in self.worker_nodes],
            "module_params": self.module_params,
        }
        self.flow_run = ModuleRunInput(**flow_run_input)

