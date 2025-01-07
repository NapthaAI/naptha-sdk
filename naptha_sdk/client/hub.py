from dotenv import load_dotenv
import os
from naptha_sdk.utils import add_credentials_to_env, get_logger, write_private_key_to_file
from naptha_sdk.user import generate_keypair
from naptha_sdk.user import get_public_key, is_hex
from surrealdb import Surreal
import traceback
from typing import Dict, List, Optional, Tuple

import jwt
from surrealdb import Surreal

from naptha_sdk.user import generate_keypair
from naptha_sdk.user import get_public_key
from naptha_sdk.utils import add_credentials_to_env, get_logger

logger = get_logger(__name__)

load_dotenv()

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
        logger.info(f"Attempting authentication for user: {username}")
        
        try:
            user = await self.surrealdb.signin({
                "NS": self.ns,
                "DB": self.db,
                "AC": "user",
                "username": username,
                "password": password,
            })
            
            self.user_id = self._decode_token(user)
            local_public_key = self.public_key or get_public_key(os.getenv("PRIVATE_KEY"))
            hub_public_key = self.user_id.split(":")[1]
            
            if local_public_key != hub_public_key:
                logger.error("Public key mismatch", extra={
                    "local_key": local_public_key,
                    "hub_key": hub_public_key
                })
                raise Exception(
                    "Public key mismatch. Please verify your private key in .env file. "
                    f"Local key: {local_public_key}, Hub key: {hub_public_key}"
                )
            
            self.token = user
            self.is_authenticated = True
            
            logger.info(f"Successfully authenticated user: {username}")
            return True, user, self.user_id
            
        except Exception as e:
            raise Exception(f"Authentication failed: {str(e)}. Please ensure you have set HUB_URL, HUB_USERNAME, and HUB_PASSWORD in the .env file, and that you have run `naptha signup` for this user.")
    
    async def signup(self, username: str, password: str, public_key: str) -> Tuple[bool, Optional[str], Optional[str]]:
        user = await self.surrealdb.signup({
            "NS": self.ns,
            "DB": self.db,
            "AC": "user",
            "name": username,
            "username": username,
            "password": password,
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

    async def list_servers(self) -> List:
        servers = await self.surrealdb.query("SELECT * FROM server;")
        return servers[0]['result']

    async def list_nodes(self, node_ip=None) -> List:
        if not node_ip:
            nodes = await self.surrealdb.query("SELECT * FROM node;")
            return nodes[0]['result']
        else:
            nodes = await self.surrealdb.query("SELECT * FROM node WHERE ip=$node_ip;", {"node_ip": node_ip})
            node = nodes[0]['result'][0]
            server_ids = node['servers']
            servers = []
            for server_id in server_ids:
                server = await self.surrealdb.select(server_id)
                servers.append(server)
            node['servers'] = servers

            alt_ports = [
                server['port'] 
                for server in servers
                if server['server_type'] in ['ws', 'grpc']
            ]
            node['ports'] = alt_ports
            return node

    async def list_agents(self, agent_name=None) -> List:
        if not agent_name:
            agents = await self.surrealdb.query("SELECT * FROM agent;")
            return agents[0]['result']
        else:
            agent = await self.surrealdb.query("SELECT * FROM agent WHERE id=$agent_name;", {"agent_name": agent_name})
            return agent[0]['result']

    async def list_tools(self, tool_name=None) -> List:
        if not tool_name:
            tools = await self.surrealdb.query("SELECT * FROM tool;")
            return tools[0]['result']
        else:
            tool = await self.surrealdb.query("SELECT * FROM tool WHERE name=$tool_name;", {"tool_name": tool_name})
            return tool[0]['result']

    async def list_orchestrators(self, orchestrator_name=None) -> List:
        if not orchestrator_name:
            orchestrators = await self.surrealdb.query("SELECT * FROM orchestrator;")
            return orchestrators[0]['result']
        else:
            orchestrator = await self.surrealdb.query("SELECT * FROM orchestrator WHERE id=$orchestrator_name;", {"orchestrator_name": orchestrator_name})
            return orchestrator[0]['result']

    async def list_environments(self, environment_name=None) -> List:
        if not environment_name:
            environments = await self.surrealdb.query("SELECT * FROM environment;")
            return environments[0]['result']
        else:
            environment = await self.surrealdb.query("SELECT * FROM environment WHERE id=$environment_name;", {"environment_name": environment_name})
            return environment[0]['result']

    async def list_personas(self, persona_name=None) -> List:
        if not persona_name:
            personas = await self.surrealdb.query("SELECT * FROM persona;")
            return personas[0]['result']
        else:
            if not "persona:" in persona_name:
                persona_name = f"persona:{persona_name}"
            persona = await self.surrealdb.query("SELECT * FROM persona WHERE id=$persona_name;", {"persona_name": persona_name})
            return persona[0]['result']
    
    async def list_memories(self, memory_name=None) -> List:
        if not memory_name:
            memories = await self.surrealdb.query("SELECT * FROM memory;")
            return memories[0]['result']
        else:
            memory = await self.surrealdb.query("SELECT * FROM memory WHERE id=$memory_name;", {"memory_name": memory_name})
            return memory[0]['result']

    async def list_kbs(self, kb_name=None) -> List:
        if not kb_name:
            kbs = await self.surrealdb.query("SELECT * FROM kb;")
            return kbs[0]['result']
        else:
            kb = await self.surrealdb.query("SELECT * FROM kb WHERE name=$kb_name;", {"kb_name": kb_name})
            return kb[0]['result']

    async def list_modules(self, module_type, module_name) -> List:
        if module_type == 'agent':
            modules = await self.surrealdb.query("SELECT * FROM agent WHERE id=$module_name;", {"module_name": module_name})
        elif module_type == 'tool':
            modules = await self.surrealdb.query("SELECT * FROM tool WHERE id=$module_name;", {"module_name": module_name})
        elif module_type == 'orchestrator':
            modules = await self.surrealdb.query("SELECT * FROM orchestrator WHERE id=$module_name;", {"module_name": module_name})
        elif module_type == 'environment':
            modules = await self.surrealdb.query("SELECT * FROM environment WHERE id=$module_name;", {"module_name": module_name})
        elif module_type == 'persona':
            modules = await self.surrealdb.query("SELECT * FROM persona WHERE id=$module_name;", {"module_name": module_name})
        elif module_type == 'memory':
            modules = await self.surrealdb.query("SELECT * FROM memory WHERE id=$module_name;", {"module_name": module_name})
        elif module_type == 'kb':
            modules = await self.surrealdb.query("SELECT * FROM kb WHERE id=$module_name;", {"module_name": module_name})
        return modules[0]['result']

    async def list_kb_content(self, kb_name: str) -> List:
        kb_content = await self.surrealdb.query("SELECT * FROM kb_content WHERE kb_id=$kb_id;", {"kb_id": f"kb:{kb_name}"})
        return kb_content[0]['result']

    async def delete_agent(self, agent_id: str) -> Tuple[bool, Optional[Dict]]:
        if ":" not in agent_id:
            agent_id = f"agent:{agent_id}".strip()
        print(f"Deleting agent: {agent_id}")
        success = await self.surrealdb.delete(agent_id)
        if success:
            print("Deleted agent")
        else:
            print("Failed to delete agent")
        return success

    async def delete_tool(self, tool_id: str) -> Tuple[bool, Optional[Dict]]:
        if ":" not in tool_id:
            tool_id = f"tool:{tool_id}".strip()
        print(f"Deleting tool: {tool_id}")
        success = await self.surrealdb.delete(tool_id)
        if success:
            print("Deleted tool")
        else:
            print("Failed to delete tool")
        return success

    async def delete_orchestrator(self, orchestrator_id: str) -> Tuple[bool, Optional[Dict]]:
        if ":" not in orchestrator_id:
            orchestrator_id = f"orchestrator:{orchestrator_id}".strip()
        print(f"Deleting orchestrator: {orchestrator_id}")
        success = await self.surrealdb.delete(orchestrator_id)
        if success:
            print("Deleted orchestrator")
        else:
            print("Failed to delete orchestrator")
        return success

    async def delete_environment(self, environment_id: str) -> Tuple[bool, Optional[Dict]]:
        if ":" not in environment_id:
            environment_id = f"environment:{environment_id}".strip()
        print(f"Deleting environment: {environment_id}")
        success = await self.surrealdb.delete(environment_id)
        if success:
            print("Deleted environment")
        else:
            print("Failed to delete environment")
        return success

    async def delete_persona(self, persona_id: str) -> Tuple[bool, Optional[Dict]]:
        if ":" not in persona_id:
            persona_id = f"persona:{persona_id}".strip()
        print(f"Deleting persona: {persona_id}")
        success = await self.surrealdb.delete(persona_id)
        if success:
            print("Deleted persona")
        else:
            print("Failed to delete persona")
        return success
    
    async def delete_memory(self, memory_id: str) -> Tuple[bool, Optional[Dict]]:
        if ":" not in memory_id:
            memory_id = f"memory:{memory_id}".strip()
        print(f"Deleting memory: {memory_id}")
        success = await self.surrealdb.delete(memory_id)
        if success:
            print("Deleted memory")
        else:
            print("Failed to delete memory")
        return success

    async def delete_kb(self, kb_id: str) -> Tuple[bool, Optional[Dict]]:
        if ":" not in kb_id:
            kb_id = f"kb:{kb_id}".strip()
        print(f"Deleting knowledge base: {kb_id}")
        success = await self.surrealdb.delete(kb_id)
        if success:
            print("Deleted knowledge base")
        else:
            print("Failed to delete knowledge base")
        return success

    async def create_agent(self, agent_config: Dict) -> Tuple[bool, Optional[Dict]]:
        if not agent_config.get('id'):
            return await self.surrealdb.create("agent", agent_config)
        else:
            return await self.surrealdb.create(agent_config.pop('id'), agent_config)

    async def create_tool(self, tool_config: Dict) -> Tuple[bool, Optional[Dict]]:
        if not tool_config.get('id'):
            return await self.surrealdb.create("tool", tool_config)
        else:
            return await self.surrealdb.create(tool_config.pop('id'), tool_config)

    async def create_orchestrator(self, orchestrator_config: Dict) -> Tuple[bool, Optional[Dict]]:
        if not orchestrator_config.get('id'):
            return await self.surrealdb.create("orchestrator", orchestrator_config)
        else:
            return await self.surrealdb.create(orchestrator_config.pop('id'), orchestrator_config)

    async def create_environment(self, environment_config: Dict) -> Tuple[bool, Optional[Dict]]:
        if not environment_config.get('id'):
            return await self.surrealdb.create("environment", environment_config)
        else:
            return await self.surrealdb.create(environment_config.pop('id'), environment_config)

    async def create_persona(self, persona_config: Dict) -> Tuple[bool, Optional[Dict]]:
        if not persona_config.get('id'):
            return await self.surrealdb.create("persona", persona_config)
        else:
            return await self.surrealdb.create(persona_config.pop('id'), persona_config)
        
    async def create_memory(self, memory_config: Dict) -> Tuple[bool, Optional[Dict]]:
        if not memory_config.get('id'):
            return await self.surrealdb.create("memory", memory_config)
        else:
            return await self.surrealdb.create(memory_config.pop('id'), memory_config)

    async def create_kb(self, kb_config: Dict) -> Tuple[bool, Optional[Dict]]:
        if not kb_config.get('id'):
            return await self.surrealdb.create("kb", kb_config)
        else:
            return await self.surrealdb.create(kb_config.pop('id'), kb_config)

    async def update_agent(self, agent_config: Dict) -> Tuple[bool, Optional[Dict]]:
        return await self.surrealdb.update("agent", agent_config)

    async def create_or_update_module(self, module_type, module_config: Dict) -> Tuple[bool, Optional[Dict]]:
        list_modules = await self.list_modules(module_type, module_config.get('id'))
        if not list_modules:
            logger.info(f"Module does not exist. Registering new module: {module_config.get('id')}")
            return await self.surrealdb.create(module_type, module_config)
        else:
            logger.info(f"Module already exists. Updating existing module: {module_config.get('id')}")
            return await self.surrealdb.update(module_config.pop('id'), module_config)

    async def close(self):
        """Close the database connection"""
        try:
            await self.surrealdb.close()
        except Exception as e:
            logger.error(f"Error closing database connection: {e}")
        finally:
            self.is_authenticated = False
            self.user_id = None
            self.token = None

    async def __aenter__(self):
        """Async enter method for context manager"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async exit method for context manager"""
        await self.close()


async def user_setup_flow(hub_url, public_key):
    async with Hub(hub_url, public_key) as hub:
        username, password = os.getenv("HUB_USERNAME"), os.getenv("HUB_PASSWORD")
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
                    public_key, private_key_path = generate_keypair(f"{username}.pem")
                    print(f"Signing up user: {username} with public key: {public_key}")
                    success, token, user_id = await hub.signup(username, password, public_key)
                    if success:
                        add_credentials_to_env(username, password, private_key_path)
                        logger.info("Sign up successful!")
                        return token, user_id
                    else:
                        logger.error("Sign up failed. Please try again.")

            case None, True, True, False:
                logger.info("User doesn't exist but some credentials are provided in .env. Using them to create new user.")
                private_key_path = None
                if not public_key:
                    logger.info("No public key provided. Generating new keypair...")
                    public_key, private_key_path = generate_keypair(f"{username}.pem")

                print(f"Signing up user: {username} with public key: {public_key}")
                success, token, user_id = await hub.signup(username, password, public_key)
                if success:
                    if private_key_path:
                        add_credentials_to_env(username, password, private_key_path)
                    logger.info("Sign up successful!")
                    return token, user_id
                else:
                    logger.error("Sign up failed.")
                    raise Exception("Sign up failed.")

            case dict(), True, True, False:
                # User exists, attempt to sign in
                logger.info("Using user credentials in .env. User exists. Attempting to sign in...")
                if os.getenv("PRIVATE_KEY") and is_hex(os.getenv("PRIVATE_KEY")):
                    write_private_key_to_file(os.getenv("PRIVATE_KEY"), username)

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
            
async def list_nodes(node_ip: str) -> List:

    hub_username = os.getenv("HUB_USERNAME")
    hub_password = os.getenv("HUB_PASSWORD")
    hub_url = os.getenv("HUB_URL")
    
    async with Hub(hub_url) as hub:
        try:
            _, _, _ = await hub.signin(hub_username, hub_password)
        except Exception as auth_error:
            raise ConnectionError(f"Failed to authenticate with Hub: {str(auth_error)}")

        node = await hub.list_nodes(node_ip=node_ip)
        return node