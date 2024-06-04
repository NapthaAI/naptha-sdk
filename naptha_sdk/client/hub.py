import jwt
import os
from surrealdb import Surreal
from typing import Dict, List, Tuple, Optional


class Hub:
    """The Hub class is the entry point into Naptha AI Hub."""

    def __init__(self, username, password, endpoint, *args, **kwargs):
        self.username = username
        self.password = password
        self.ns = "naptha"
        self.db = "naptha"
        self.surrealdb = Surreal(endpoint)
        self.__storedargs = username, password, args, kwargs
        self.async_initialized = False
        
    async def __ainit__(self, username, password, *args, **kwargs):
        """Async constructor"""
        success, token, user_id = await self._authenticated_db()
        self.user_id = user_id
        self.token = token

    async def __initobj(self):
        """Crutch used for __await__ after spawning"""
        assert not self.async_initialized
        self.async_initialized = True
        # pass the parameters to __ainit__ that passed to __init__
        await self.__ainit__(self.__storedargs[0], self.__storedargs[1], *self.__storedargs[2], **self.__storedargs[3])
        return self

    def __await__(self):
        return self.__initobj().__await__()

    async def _authenticated_db(self):
        try:
            await self.surrealdb.connect()
            await self.surrealdb.use(namespace=self.ns, database=self.db)
            success, token, user_id = await self.signin()
            self.is_authenticated = True
            return success, token, user_id
        except Exception as e:
            print(f"Authentication failed: {e}")
            raise

    def _decode_token(self, token: str) -> str:
        return jwt.decode(token, options={"verify_signature": False})["ID"]

    async def signin(self) -> Tuple[bool, Optional[str], Optional[str]]:
        try:
            user = await self.surrealdb.signin(
                {
                    "NS": self.ns,
                    "DB": self.db,
                    "SC": "user",
                    "username": self.username,
                    "password": self.password,
                },
            )
        except Exception as e:
            print(f"Authentication failed: {e}")
            return False, None, None
        user_id = self._decode_token(user)
        return True, user, user_id

    async def get_user(self, user_id: str) -> Optional[Dict]:
        return await self.surrealdb.select(user_id)

    async def get_credits(self) -> List:
        user = await self.get_user(self.user_id)
        return user['credits']

    async def get_node(self, node_id: str) -> Optional[Dict]:
        return await self.surrealdb.select(node_id)

    async def list_nodes(self) -> List:
        nodes = await self.surrealdb.query("SELECT * FROM node;")
        return nodes[0]['result']

    async def list_modules(self, module_name=None) -> List:
        if not module_name:
            modules = await self.surrealdb.query("SELECT * FROM module;")
            return modules[0]['result']
        else:
            module = await self.surrealdb.query("SELECT * FROM module WHERE id=$module_name;", {"module_name": module_name})
            return module[0]['result'][0]

    async def list_tasks(self) -> List:
        tasks = await self.surrealdb.query("SELECT * FROM lot;")
        return tasks[0]['result']

    async def list_rfps(self) -> List:
        rfps = await self.surrealdb.query("SELECT * FROM auction;")
        return rfps[0]['result']

    async def list_rfps_from_consumer(self, consumer: Dict) -> List:
        proposals = await self.surrealdb.query("SELECT * FROM auction WHERE node=$node;", consumer)
        proposals = proposals[0]['result']
        return proposals

    async def submit_proposal(self, proposal: Dict) -> Tuple[bool, Optional[Dict]]:
        proposal = await self.surrealdb.query("RELATE $me->requests_to_bid_on->$auction SET amount=1.0;", proposal)
        return proposal[0]['result'][0]

    def list_active_proposals(self):
        pass

    async def list_accepted_proposals(self, plan_id=None) -> List:
        if not plan_id:
            proposals = await self.surrealdb.query("SELECT * FROM wins WHERE in=$user;", {"user": self.user_id})
            return proposals[0]['result']
        else:
            proposals = await self.surrealdb.query("SELECT * FROM wins WHERE in=$user AND out=$plan;", {"user": self.user_id, "plan": plan_id})
            return proposals[0]['result'][0]
