import jwt
import os
from naptha_sdk.utils import add_credentials_to_env, get_logger
from naptha_sdk.user import generate_keypair
from naptha_sdk.user import get_public_key
from surrealdb import Surreal
import traceback
from typing import Dict, List, Optional, Tuple

logger = get_logger(__name__)


class Hub:
    """The Hub class is the entry point into Naptha AI Hub."""

    def __init__(self, hub_url, public_key=None, *args, **kwargs):
        self.hub_url = hub_url
        self.public_key = public_key
        self.ns = "naptha"
        self.db = "naptha"
        self.surrealdb = Surreal(hub_url)
        self.is_authenticated = False
        self.user_id = None
        self.token = None
        
        logger.info(f"Hub URL: {hub_url}")

    async def connect(self):
        """Connect to the database and authenticate"""
        if not self.is_authenticated:
            try:
                await self.surrealdb.connect()
                await self.surrealdb.use(namespace=self.ns, database=self.db)
            except Exception as e:
                logger.error(f"Connection failed: {e}")
                raise

    def _decode_token(self, token: str) -> str:
        return jwt.decode(token, options={"verify_signature": False})["ID"]

    async def signin(self, username: str, password: str) -> Tuple[bool, Optional[str], Optional[str]]:
        try:
            print("Signing in to hub with username: ", username)
            user = await self.surrealdb.signin(
                {
                    "NS": self.ns,
                    "DB": self.db,
                    "SC": "user",
                    "username": username,
                    "password": password,
                },
            )
            self.user_id = self._decode_token(user)
            self.token = user
            self.is_authenticated = True
            print("User ID: ", self.user_id)
            return True, user, self.user_id
        except Exception as e:
            print(f"Authentication failed: {e}")
            print("Full traceback: ", traceback.format_exc())
            return False, None, None

    async def signup(self, username: str, password: str, public_key: str) -> Tuple[bool, Optional[str], Optional[str]]:

        user = await self.surrealdb.signup({
            "NS": self.ns,
            "DB": self.db,
            "SC": "user",
            "name": username,
            "username": username,
            "password": password,
            "invite": "DZHA4ZTK",
            "public_key": public_key,
        })
        if not user:
            return False, None, None
        self.user_id = self._decode_token(user)
        return True, user, self.user_id


    async def get_user(self, user_id: str) -> Optional[Dict]:
        return await self.surrealdb.select(user_id)

    async def get_user_by_username(self, username: str) -> Optional[Dict]:
        result = await self.surrealdb.query(
            "SELECT * FROM user WHERE username = $username LIMIT 1",
            {"username": username}
        )
        if result and result[0]["result"]:
            return result[0]["result"][0]
        return None

    async def get_user_by_public_key(self, public_key: str) -> Optional[Dict]:
        result = await self.surrealdb.query(
            "SELECT * FROM user WHERE public_key = $public_key LIMIT 1",
            {"public_key": public_key}
        )
        if result and result[0]["result"]:
            return result[0]["result"][0]
        return None

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

    async def delete_module(self, module_id: str) -> Tuple[bool, Optional[Dict]]:
        if ":" not in module_id:
            module_id = f"module:{module_id}".strip()
        print(f"Deleting module: {module_id}")
        success = await self.surrealdb.delete(module_id)
        if success:
            print("Deleted module")
        else:
            print("Failed to delete module")
        return success

    async def create_module(self, module_config: Dict) -> Tuple[bool, Optional[Dict]]:
        if not module_config.get('id'):
            return await self.surrealdb.create("module", module_config)
        else:
            return await self.surrealdb.create(module_config.pop('id'), module_config)

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

    async def close(self):
        """Close the database connection"""
        if self.is_authenticated:
            try:
                await self.surrealdb.close()
            except Exception as e:
                logger.error(f"Error closing database connection: {e}")
            finally:
                self.is_authenticated = False
                self.user_id = None
                self.token = None
                logger.info("Database connection closed")

    async def __aenter__(self):
        """Async enter method for context manager"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async exit method for context manager"""
        await self.close()


async def user_setup_flow(hub_url, public_key):
    async with Hub(hub_url, public_key) as hub:
        username, password = os.getenv("HUB_USER"), os.getenv("HUB_PASS")
        username_exists, password_exists = len(username) > 1, len(password) > 1
        public_key = get_public_key(os.getenv("PRIVATE_KEY")) if os.getenv("PRIVATE_KEY") else None
        logger.info(f"Checking if user exists... User: {username}")
        user = await hub.get_user_by_username(username)
        user_public_key = await hub.get_user_by_public_key(public_key)
        existing_public_key_user = user_public_key is not None and user_public_key.get('username') != username

        match user, username_exists, password_exists, existing_public_key_user:
            case _, True, _, True:
                # Public key exists and doesn't match the provided username and password
                raise Exception(f"Using user credentials in .env. User with public key {public_key} already exists but doesn't match the provided username and password. Please use a different private key (or set blank in the .env file to randomly generate with launch.sh).")

            case _, False, False, True:
                # Public key exists and no username/password provided
                raise Exception(f"Using private key in .env. User with public key {public_key} already exists. Cannot create new user. Please use a different private key (or set blank in the .env file to randomly generate with launch.sh).")

            case None, False, _, False:
                # User doesn't exist and credentials are missing
                logger.info("No credentials provided in .env.")
                create_new = input("Would you like to create a new user? (yes/no): ").lower()
                if create_new != 'yes':
                    raise Exception("User does not exist and new user creation was declined.")
                logger.info("Creating new user...")
                while True:
                    username = input("Enter username: ")
                    existing_user = await hub.get_user_by_username(username)
                    if existing_user:
                        print(f"Username '{username}' already exists. Please choose a different username.")
                        continue
                    password = input("Enter password: ")
                    public_key, private_key = generate_keypair()
                    print(f"Signing up user: {username} with public key: {public_key}")
                    success, token, user_id = await hub.signup(username, password, public_key)
                    if success:
                        add_credentials_to_env(username, password, private_key)
                        logger.info("Sign up successful!")
                        return token, user_id
                    else:
                        logger.error("Sign up failed. Please try again.")

            case None, True, True, False:
                # User doesn't exist but credentials are provided
                print(f"Using user credentials in .env. Signing up user: {username} with public key: {public_key}")
                success, token, user_id = await hub.signup(username, password, public_key)
                if success:
                    logger.info("Sign up successful!")
                    return token, user_id
                else:
                    logger.error("Sign up failed.")
                    raise Exception("Sign up failed.")

            case dict(), True, True, False:
                # User exists, attempt to sign in
                logger.info("Using user credentials in .env. User exists. Attempting to sign in...")
                success, token, user_id = await hub.signin(username, password)
                if success:
                    logger.info("Sign in successful!")
                    return token, user_id
                else:
                    logger.error("Sign in failed. Please check your credentials in the .env file.")
                    raise Exception("Sign in failed. Please check your credentials in the .env file.")

            case _:
                logger.error("Unexpected case encountered in user setup flow.")
                raise Exception("Unexpected error in user setup. Please check your configuration and try again.")
                    