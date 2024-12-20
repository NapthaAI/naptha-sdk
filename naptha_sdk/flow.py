from naptha_sdk.schemas import AgentRunInput


class Flow:
    def __init__(self, name, user_id, agent_nodes, agent_run_params):
        self.name = name
        self.user_id = user_id
        self.agent_nodes = agent_nodes
        self.agent_run_params = agent_run_params

        flow_run_input = {
            "agent_name": self.name,
            "agent_run_params_type": "package",
            "consumer_id": self.user_id,
            "agent_nodes": [w.node_url for w in self.agent_nodes],
            "agent_run_params": self.agent_run_params,
        }
        self.flow_run = AgentRunInput(**flow_run_input)

