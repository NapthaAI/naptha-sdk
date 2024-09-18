import logging
import os
import yaml

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

def add_credentials_to_env(username, password, private_key):
    env_file_path = os.path.join(os.getcwd(), '.env')
    updated_lines = []
    hub_user_found = False
    hub_pass_found = False
    private_key_found = False

    # Read the existing .env file
    with open(env_file_path, 'r') as env_file:
        for line in env_file:
            if line.startswith('HUB_USER='):
                updated_lines.append(f"HUB_USER={username}\n")
                hub_user_found = True
            elif line.startswith('HUB_PASS='):
                updated_lines.append(f"HUB_PASS={password}\n")
                hub_pass_found = True
            elif line.startswith('PRIVATE_KEY='):
                updated_lines.append(f"PRIVATE_KEY={private_key}\n")
                private_key_found = True
            else:
                updated_lines.append(line)

    # Append new credentials if not found
    if not hub_user_found:
        updated_lines.append(f"HUB_USER={username}\n")
    if not hub_pass_found:
        updated_lines.append(f"HUB_PASS={password}\n")
    if not private_key_found:
        updated_lines.append(f"PRIVATE_KEY={private_key}\n")

    # Write the updated content back to the .env file
    with open(env_file_path, 'w') as env_file:
        env_file.writelines(updated_lines)

    print("Your credentials and private key have been updated in the .env file. You can now use these credentials to authenticate in future sessions.")

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