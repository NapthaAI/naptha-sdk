from huggingface_hub import HfApi, login
from naptha_sdk.client.hub import Hub
from naptha_sdk.client.node import Node
from naptha_sdk.utils import AsyncMixin
from typing import Dict, List, Tuple

class Naptha(AsyncMixin):
    """The entry point into Naptha."""

    def __init__(self,
            user,
            hub_username, 
            hub_password, 
            hf_username,
            hf_access_token,
            hub_url="ws://node.naptha.ai:3001/rpc",
            node_url="http://node.naptha.ai:7001",
            routing_url=None,
            indirect_node_id=None,
            *args, 
            **kwargs
    ):
        
        self.user = user
        self.hub_url = hub_url
        self.hf_username = hf_username
        login(hf_access_token)
        self.hf = HfApi()
        self.node_url = node_url
        self.routing_url = routing_url
        self.indirect_node_id = indirect_node_id
        self.node = Node(
            node_url=node_url,
            routing_url=routing_url,
            indirect_node_id=indirect_node_id
        )
        super().__init__()

    async def __ainit__(self,
            user,
            hub_username, 
            hub_password, 
            hub_url,
            node_url,
            routing_url,
            indirect_node_id,
            *args, 
            **kwargs):
        """Async constructor"""
        self.hub = await Hub(hub_username, hub_password, hub_url)
