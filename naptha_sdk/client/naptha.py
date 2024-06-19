
from naptha_sdk.client.hub import Hub
from naptha_sdk.client.node import Node
from naptha_sdk.client.services import Services
from typing import Dict, List, Tuple

class Naptha:
    """The entry point into Naptha."""

    def __init__(self,
            user,
            hub_username, 
            hub_password, 
            hub_url,
            node_url,
            routing_url,
            indirect_node_id,
            *args, 
            **kwargs
    ):
        
        self.user = user
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
        self.__storedargs = user, hub_username, hub_password, hub_url, node_url, args, kwargs
        self.async_initialized = False

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

    async def __initobj(self):
        """Crutch used for __await__ after spawning"""
        assert not self.async_initialized
        self.async_initialized = True
        await self.__ainit__(
            self.__storedargs[0], 
            self.__storedargs[1], 
            self.__storedargs[2], 
            self.__storedargs[3], 
            self.__storedargs[4], 
            self.__storedargs[5], 
            self.__storedargs[6],
        )
        return self

    def __await__(self):
        return self.__initobj().__await__()
