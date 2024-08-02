from datetime import datetime
import functools
import json
import os
import time
import traceback
import inspect
from naptha_sdk.utils import AsyncMixin

class MultiAgentService(AsyncMixin):
    def __init__(self, naptha, name, fn):
        self.naptha
        self.name = name
        self.fn = fn

        mas_run_input = {
            "name": self.name,
            "type": "template",
            "consumer_id": naptha.user.id,
            "orchestrator_node": naptha.node_url,
            "worker_nodes": [w.node_url for w in self.worker_nodes],
            "module_params": self.module_params,
        }
        self.mas_run = mas_run_input

