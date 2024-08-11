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
            self.agent_services.append(AgentService(self.naptha, name=name, fn=func, worker_node_url=worker_node_url))
            return func
        return decorator

    def publish_agent_packages(self):
        for agent_service in self.agent_services:
            agent_service.publish_package()

    async def register_agent_modules(self):
        for agent_service in self.agent_services:
            await agent_service.register_module()

    async def register_agent_services(self):
        for agent_service in self.agent_services:
            await agent_service.register_service()

    def multi_agent_service(self, name):
        def decorator(func):
            self.multi_agent_service = MultiAgentService(self.naptha, name=name, fn=func)
            return func
        return decorator

    def publish_multi_agent_packages(self):
        for multi_agent_service in self.multi_agent_services:
            multi_agent_service.publish_package()

    async def register_multi_agent_modules(self):
        for multi_agent_service in self.multi_agent_services:
            await multi_agent_service.register_module()

    async def register_multi_agent_services(self):
        for multi_agent_service in self.multi_agent_services:
            await multi_agent_service.register_service()

    async def run(self, run_params):
        worker_node_urls = [agent_service.worker_node_url for agent_service in self.agent_services]
        return await self.multi_agent_service(run_params, worker_node_urls=worker_node_urls)
