import functools
from naptha_sdk.agent_service import AgentService
from naptha_sdk.mas import MultiAgentService

class App:
    def __init__(self, naptha):
        self.naptha = naptha
        self.agent_services = []
        self.multi_agent_services = []

    def agent_service(self, name, worker_node_url):
        def decorator(func):
            self.agent_services.append({"name": name, "func": func, "worker_node_url": worker_node_url})
            return func
        return decorator

    async def register_agent_services(self):
        for agent_service in self.agent_services:
            await AgentService(self.naptha, name=agent_service["name"], fn=agent_service["func"], worker_node_url=agent_service["worker_node_url"])

    def multi_agent_service(self, name):
        def decorator(func):
            self.multi_agent_services.append({"name": name, "func": func})
            return func
        return decorator

    async def register_multi_agent_services(self):
        for multi_agent_service in self.multi_agent_services:
            self.multiplayer_chat = await MultiAgentService(self.naptha, name=multi_agent_service["name"], fn=multi_agent_service["func"])

    async def run(self, run_params):
        worker_node_urls = [agent_service["worker_node_url"] for agent_service in self.agent_services]
        return await self.multiplayer_chat(run_params, worker_node_urls=worker_node_urls)
