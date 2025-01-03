import logging
import os
import yaml
from naptha_sdk.schemas import NodeConfigUser

def get_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

def load_yaml(cfg_path):
    with open(cfg_path, "r") as file:
        cfg = yaml.load(file, Loader=yaml.FullLoader)
    return cfg

def add_credentials_to_env(username, password, private_key_path):
    env_file_path = os.path.join(os.getcwd(), '.env')
    updated_lines = []
    hub_user_found = False
    hub_pass_found = False
    private_key_found = False

    # Read the existing .env file
    with open(env_file_path, 'r') as env_file:
        for line in env_file:
            if line.startswith('HUB_USERNAME='):
                updated_lines.append(f"HUB_USERNAME={username}\n")
                hub_user_found = True
            elif line.startswith('HUB_PASSWORD='):
                updated_lines.append(f"HUB_PASSWORD={password}\n")
                hub_pass_found = True
            elif line.startswith('PRIVATE_KEY='):
                updated_lines.append(f"PRIVATE_KEY={private_key_path}\n")
                private_key_found = True
            else:
                updated_lines.append(line)

    # Append new credentials if not found
    if not hub_user_found:
        updated_lines.append(f"HUB_USERNAME={username}\n")
    if not hub_pass_found:
        updated_lines.append(f"HUB_PASSWORD={password}\n")
    if not private_key_found:
        updated_lines.append(f"PRIVATE_KEY={private_key_path}\n")

    # Write the updated content back to the .env file
    with open(env_file_path, 'w') as env_file:
        env_file.writelines(updated_lines)

    print("Your credentials have been updated in the .env file. You can now use these credentials to authenticate in future sessions.")

def write_private_key_to_file(private_key, username):
    private_key_file_path = os.path.join(os.getcwd(), f'{username}.pem')
    with open(private_key_file_path, 'w') as file:
        file.write(private_key)
    
    update_private_key_in_env(private_key_file_path)    

def update_private_key_in_env(private_key_path):
    env_file_path = os.path.join(os.getcwd(), '.env')
    updated_lines = []
    private_key_found = False

    with open(env_file_path, 'r') as env_file:
        for line in env_file:
            if line.startswith('PRIVATE_KEY='):
                updated_lines.append(f"PRIVATE_KEY={private_key_path}\n")
                private_key_found = True
            else:
                updated_lines.append(line)

    if not private_key_found:
        updated_lines.append(f"PRIVATE_KEY={private_key_path}\n")

    with open(env_file_path, 'w') as env_file:
        env_file.writelines(updated_lines)

    print("Your private key have been updated in the .env file")

class AsyncMixin:
    def __init__(self, *args, **kwargs):
        """
        Standard constructor used for arguments pass
        Do not override. Use __ainit__ instead
        """
        self.__storedargs = args, kwargs
        self.async_initialized = False

    async def __ainit__(self, *args, **kwargs):
        """Async constructor, you should implement this"""

    async def __initobj(self):
        """Crutch used for __await__ after spawning"""
        assert not self.async_initialized
        self.async_initialized = True
        # pass the parameters to __ainit__ that passed to __init__
        await self.__ainit__(*self.__storedargs[0], **self.__storedargs[1])
        return self

    def __await__(self):
        return self.__initobj().__await__()
    
def node_to_url(node_schema: NodeConfigUser):
    return f"http://{node_schema.ip}:{node_schema.http_port}"
    
def url_to_node(url: str):
    protocol = url.split('://')[0]
    host = url.split('://')[1].split(':')[0] 
    http_port = int(url.split(':')[-1])
    return NodeConfigUser(ip=host, http_port=http_port, server_type=protocol)