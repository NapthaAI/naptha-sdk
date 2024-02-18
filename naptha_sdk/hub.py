import jwt
import os
from surrealdb import Surreal
from typing import Dict, List, Tuple, Optional


class Hub:
    """The Hub class is the entry point into NapthaAI Hub."""

    def __init__(self, username, password, endpoint, *args, **kwargs):
        self.username = username
        self.password = password
        self.ns = "algovera"
        self.db = "algovera"
        self.surrealdb = Surreal(endpoint)
        self.__storedargs = username, password, args, kwargs
        self.async_initialized = False
        
    async def __ainit__(self, username, password, *args, **kwargs):
        """Async constructor, you should implement this"""
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

    async def list_sellers(self) -> List:
        return await self.surrealdb.query("SELECT * FROM auction;")

    async def get_credits(self) -> List:
        user = await self.get_user(self.user_id)
        return user['credits']

    async def get_node(self, node_id: str) -> Optional[Dict]:
        return await self.surrealdb.select(node_id)

    async def list_nodes(self) -> List:
        return await self.surrealdb.select("node")

    async def list_modules(self, module_id=None) -> List:
        if not module_id:
            modules = await self.surrealdb.query("SELECT * FROM module;")
            return modules[0]['result']
        else:
            module = await self.surrealdb.query("SELECT * FROM module WHERE id=$module_id;", {"module_id": module_id})
            return module[0]['result'][0]

    async def list_plans(self, node: Dict) -> List:
        plans = await self.surrealdb.query("SELECT * FROM auction WHERE node=$node;", node)
        plans = plans[0]['result']
        return plans

    async def list_purchases(self, plan_id=None) -> List:
        if not plan_id:
            purchases = await self.surrealdb.query("SELECT * FROM wins WHERE in=$user;", {"user": self.user_id})
            return purchases[0]['result']
        else:
            purchases = await self.surrealdb.query("SELECT * FROM wins WHERE in=$user AND out=$plan;", {"user": self.user_id, "plan": plan_id})
            return purchases[0]['result'][0]

    async def purchase(self, purchase: Dict) -> Tuple[bool, Optional[Dict]]:
        purchase = await self.surrealdb.query("RELATE $me->requests_to_bid_on->$auction SET amount=1.0;", purchase)
        return purchase[0]['result'][0]