from dotenv import load_dotenv
import os
from naptha_sdk.utils import add_credentials_to_env, get_logger, write_private_key_to_file
from naptha_sdk.user import generate_keypair, get_public_key, is_hex
from naptha_sdk.schemas import SecretInput
from surrealdb import Surreal
from typing import Dict, List, Optional, Tuple
import jwt

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

            node_communication_ports = [
                server['port'] 
                for server in servers
                if server['node_communication_protocol'] in ['ws', 'grpc']
            ]
            node['ports'] = node_communication_ports
            return node
        
    async def list_secrets(self) -> List:
        secrets = await self.surrealdb.query("SELECT * FROM api_secrets;")
        if len(secrets) > 0:
            return secrets[0].get('result', [])
        else:
            return []

    async def create_module(self, module_type: str, module_config: Dict) -> Tuple[bool, Optional[Dict]]:
        """
        Unified method to create any module type (agent, tool, orchestrator, etc.)
        
        Args:
            module_type: Type of module ('agent', 'tool', 'orchestrator', 'environment', 'persona', 'memory', 'kb')
            module_config: Configuration dictionary for the module
            
        Returns:
            Created module data
        """
        valid_types = {'agent', 'tool', 'orchestrator', 'environment', 'persona', 'memory', 'kb'}
        if module_type not in valid_types:
            raise ValueError(f"Invalid module type. Must be one of: {', '.join(valid_types)}")

        if not module_config.get('id'):
            module = await self.surrealdb.create(module_type, module_config)
        else:
            module_id = module_config.pop('id')
            module = await self.surrealdb.create(module_id, module_config)
            
        logger.info(f"Created {module_type}: {module}")
        return module

    async def update_module(self, module_type: str, module_config: Dict) -> Tuple[bool, Optional[Dict]]:
        """
        Unified method to update any module type (agent, tool, orchestrator, etc.)
        
        Args:
            module_type: Type of module ('agent', 'tool', 'orchestrator', 'environment', 'persona', 'memory', 'kb')
            module_config: Configuration dictionary for the module
            
        Returns:
            Tuple containing the updated module data
        """
        valid_types = {'agent', 'tool', 'orchestrator', 'environment', 'persona', 'memory', 'kb'}
        if module_type not in valid_types:
            raise ValueError(f"Invalid module type. Must be one of: {', '.join(valid_types)}")

        if not module_config.get('id'):
            module = await self.surrealdb.update(module_type, module_config)
        else:
            module_id = module_config.pop('id')
            existing = await self.surrealdb.select(module_id)
            if existing:
                author = existing['author']
                assert author == self.user_id, f"You are not authorized to update this module. Author: {author}, Current user: {self.user_id}"
                updated_data = {**existing, **module_config}
                module = await self.surrealdb.update(module_id, updated_data)
            else:
                raise Exception(f"No existing {module_type} found with id {module_id}")
            
        logger.info(f"Updated {module_type}: {module}")
        return module

    async def delete_module(self, module_type: str, module_id: str) -> Tuple[bool, Optional[Dict]]:
        """
        Unified method to delete any module type (agent, tool, orchestrator, etc.)
        
        Args:
            module_type: Type of module ('agent', 'tool', 'orchestrator', 'environment', 'persona', 'memory', 'kb')
            module_id: ID of the module to delete
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        valid_types = {'agent', 'tool', 'orchestrator', 'environment', 'persona', 'memory', 'kb'}
        if module_type not in valid_types:
            raise ValueError(f"Invalid module type. Must be one of: {', '.join(valid_types)}")

        if ":" not in module_id:
            module_id = f"{module_type}:{module_id}".strip()
        
        existing = await self.surrealdb.select(module_id)
        if existing:
            author = existing['author']
            assert author == self.user_id, f"You are not authorized to delete this module. Author: {author}, Current user: {self.user_id}"

        logger.info(f"Deleting {module_type}: {module_id}")
        success = await self.surrealdb.delete(module_id)
        
        if success:
            logger.info(f"Deleted {module_type}")
        else:
            logger.warning(f"Failed to delete {module_type}")
            
        return success

    async def list_modules(self, module_type: str, module_name: Optional[str] = None) -> List:
        """
        Unified method to list any module type (agent, tool, orchestrator, etc.)
        
        Args:
            module_type: Type of module ('agent', 'tool', 'orchestrator', 'environment', 'persona', 'memory', 'kb')
            module_name: Optional name/id of specific module to retrieve
            
        Returns:
            List of modules or specific module if module_name is provided
        """
        valid_types = {'agent', 'tool', 'orchestrator', 'environment', 'persona', 'memory', 'kb'}
        if module_type not in valid_types:
            raise ValueError(f"Invalid module type. Must be one of: {', '.join(valid_types)}")

        if not module_name:
            result = await self.surrealdb.query(f"SELECT * FROM {module_type};")
            return result[0]['result']
        else:
            # Handle special case for personas where we need to add prefix
            if module_type == 'persona' and not "persona:" in module_name:
                module_name = f"persona:{module_name}"
                
            # For specific module queries, use the id field
            result = await self.surrealdb.query(
                f"SELECT * FROM {module_type} WHERE id=$module_name;",
                {"module_name": module_name}
            )
            return result[0]['result']

    async def create_or_update_module(self, module_type, module_config: Dict) -> Tuple[bool, Optional[Dict]]:
        list_modules = await self.list_modules(module_type, module_config.get('id'))
        if not list_modules:
            logger.info(f"Module does not exist. Registering new module: {module_config.get('id')}")
            return await self.surrealdb.create(module_type, module_config)
        else:
            logger.info(f"Module already exists. Updating existing module: {module_config.get('id')}")
            return await self.surrealdb.update(module_config.pop('id'), module_config)
        
    def prepare_batch_query(self, secret_config: List[SecretInput], existing_secrets: List[SecretInput], update:bool = False) -> str:
        existing_secrets_dict = {secret.key_name for secret in existing_secrets}
        records_to_insert = []
        records_to_update = []
        
        for secret in secret_config:
            user_id = secret.user_id.replace("<record>", "").strip()
            key_name = secret.key_name
            key_value = secret.secret_value

            if not existing_secrets_dict or key_name not in existing_secrets_dict:
                records_to_insert.append({
                    "user_id": user_id,
                    "key_name": key_name, 
                    "secret_value": key_value
                })
            else:
                if update:
                    records_to_update.append({
                        "secret_value": key_value,
                        "user_id": user_id,
                        "key_name": key_name
                    })

        insert_query = ""
        if records_to_insert:
            insert_query = "INSERT INTO api_secrets $records;"

        update_query = ""
        if records_to_update:
            update_query = "UPDATE api_secrets SET secret_value = $secret_value WHERE user_id = $user_id AND key_name = $key_name;"

        return {
            "insert_query": insert_query,
            "insert_params": {"records": records_to_insert},
            "update_query": update_query,
            "update_params": records_to_update
        }
    
    async def create_secret(self, secret_config: List[SecretInput], update: bool = False, existing_secrets: List[SecretInput] = []) -> str:
        try:
            user_id = secret_config[0].user_id.replace("<record>", "").strip()
            if not user_id:
                return "Invalid user ID"

            query_data = self.prepare_batch_query(secret_config, existing_secrets, update)

            if not (query_data["insert_query"] or query_data["update_query"]):
                return "Records already exist"

            try:
                transaction_query = "BEGIN TRANSACTION;"
                
                if query_data["insert_query"]:
                    transaction_query += "\n" + query_data["insert_query"]
                
                if query_data["update_query"]:
                    for i, _ in enumerate(query_data["update_params"]):
                        parameterized_query = query_data["update_query"].replace(
                            "$secret_value", f"$secret_value_{i}"
                        ).replace(
                            "$user_id", f"$user_id_{i}"
                        ).replace(
                            "$key_name", f"$key_name_{i}"
                        )
                        transaction_query += f"\n{parameterized_query}"
                
                transaction_query += "\nCOMMIT TRANSACTION;"

                params = {}
                if query_data["insert_params"]:
                    params.update(query_data["insert_params"])
                
                for i, update_params in enumerate(query_data["update_params"]):
                    params.update({
                        f"secret_value_{i}": update_params["secret_value"],
                        f"user_id_{i}": update_params["user_id"],
                        f"key_name_{i}": update_params["key_name"]
                    })

                results = await self.surrealdb.query(transaction_query, params)

                if all(result.get('status') == 'OK' for result in results) and any(result.get('result') for result in results):
                    return "Records updated successfully"
                else:
                    return "Operation failed: Database error"

            except Exception as e:
                logger.error(f"Secret creation failed: {str(e)}")
                return f"Operation failed: {type(e).__name__}"

        except Exception as e:
            logger.error(f"Secret creation failed: {str(e)}")
            return "Operation failed: Invalid input"
        
    async def delete_secret(self, key_name: str) -> str:
        try:
            await self.surrealdb.query(f"DELETE FROM api_secrets WHERE key_name = $key_name;", {"key_name": key_name})
            return "Secret deleted successfully"
        except Exception as e:
            logger.error(f"Secret deletion failed: {str(e)}")
            return "Operation failed: Invalid input"

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