
from naptha_sdk.client.hub import Hub
from naptha_sdk.client.node import Node
from naptha_sdk.client.services import Services
from typing import Dict, List, Tuple

class Naptha:
    """The entry point into Naptha."""

    def __init__(self,
            hub_url,
            node_url,
            routing_url=None,
            indirect_node_id=None,
            public_key=None,
            hub_username=None, 
            hub_password=None, 
            *args, 
            **kwargs
    ):
        
        self.public_key = public_key
        self.hub_url = hub_url
        self.node_url = node_url
        self.routing_url = routing_url
        self.indirect_node_id = indirect_node_id
        self.node = Node(
            node_url=node_url,
            routing_url=routing_url,
            indirect_node_id=indirect_node_id
        )
        self.services = Services()
        self.hub = Hub(hub_url, public_key)  

    async def __aenter__(self):
        """Async enter method for context manager"""
        await self.hub.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async exit method for context manager"""
        await self.hub.close()
