from dotenv import load_dotenv
from git import Repo
import importlib.util
import ipfshttpclient
import json
from naptha_sdk.client.hub import Hub
from naptha_sdk.utils import get_logger
import os
from pathlib import Path
import re
from pydantic import BaseModel
import subprocess
import tempfile
import textwrap
import tomlkit
import yaml
import zipfile
import fnmatch

load_dotenv()
logger = get_logger(__name__)

IPFS_GATEWAY_URL="/dns/provider.akash.pro/tcp/31832/http"
AGENT_DIR = "agent_pkgs"

# Certain packages cause issues with dependencies and can be slow to resolve, better to specify ranges
PACKAGE_VERSIONS = {
    "crewai": "^0.41.1",
    "crewai_tools": ">=0.4.6,<0.5.0",
    "embedchain": ">=0.1.113,<0.2.0",
}

def init_agent_package(package_name):
    subprocess.run(["poetry", "new", f"{AGENT_DIR}/{package_name}"])
    subprocess.run(["git", "init", f"{AGENT_DIR}/{package_name}"])

def is_std_lib(module_name):
    try:
        module_spec = importlib.util.find_spec(module_name)
        return module_spec is not None and 'site-packages' not in module_spec.origin
    except ImportError:
        return False

def add_dependencies_to_pyproject(package_name, packages):
    # Adds dependencies with wildcard versioning
    with open(f"{AGENT_DIR}/{package_name}/pyproject.toml", 'r', encoding='utf-8') as file:
        data = tomlkit.parse(file.read())

    dependencies = data['tool']['poetry']['dependencies']
    dependencies["python"] = ">=3.10,<3.13"
    dependencies["naptha-sdk"] = {
        "git": "https://github.com/NapthaAI/naptha-sdk.git",
        "branch": "feat/run-agent-tools"
    }

    packages_to_add = []
    for package in packages:
        curr_package = package['module'].split('.')[0]
        if curr_package not in packages_to_add and not is_std_lib(curr_package):
            dependencies[curr_package] = PACKAGE_VERSIONS.get(curr_package, "*")
    dependencies["python-dotenv"] = "*"

    # Serialize the TOML data and write it back to the file
    with open(f"{AGENT_DIR}/{package_name}/pyproject.toml", 'w', encoding='utf-8') as file:
        file.write(tomlkit.dumps(data))

def render_agent_code(agent_name, agent_code, obj_name, local_modules, selective_import_modules, standard_import_modules, variable_modules, union_modules, params):
    # Add the imports for installed modules (e.g. crewai)
    content = ''

    for module in standard_import_modules:
        line = f'import {module["name"]} \n'
        content += line

    for module in selective_import_modules:
        line = f'from {module["module"]} import {module["name"]} \n'
        content += line

    for module in variable_modules:
        if module["module"] and module["import_needed"]:
            content += f'from {module["module"]} import {module["name"]} \n'

    if any('crewai' in module['module'] for module in selective_import_modules):
        content += "from crewai import Task\n"

    for module in union_modules:
        content += module['source']

    # Add the naptha imports and logger setup
    naptha_imports = f'''from dotenv import load_dotenv
from {agent_name}.schemas import InputSchema
from naptha_sdk.utils import get_logger

logger = get_logger(__name__)

load_dotenv()

'''
    content += naptha_imports
    for module in selective_import_modules:
        if 'source' in module and module['source']:
            content += module['source'] + "\n"

    # Add the source code for the local modules 
    for module in local_modules:
        content += module['source'] + "\n"

    for module in variable_modules:
        content += module['source'] + "\n"

    # Convert class method to function
    agent_code = agent_code.replace('self.', '')
    agent_code = agent_code.replace('self', '')

    content += textwrap.dedent(agent_code) + "\n\n"

    param_str = ", ".join(f"inputs.{name}" for name, info in params.items())

    # Define the new function signature
    content += f"""def run(inputs: InputSchema, *args, **kwargs):
    {agent_name}_0 = {obj_name}({param_str})

    tool_input_class = globals().get(inputs.tool_input_type)
    tool_input = tool_input_class(**inputs.tool_input_value)
    method = getattr({agent_name}_0, inputs.tool_name, None)

    return method(tool_input)

if __name__ == "__main__":
    from naptha_sdk.utils import load_yaml
    from {agent_name}.schemas import InputSchema

    cfg_path = "{agent_name}/component.yaml"
    cfg = load_yaml(cfg_path)

    # You will likely need to change the inputs dict
    inputs = {{"tool_name": "execute_task", "tool_input_type": "Task", "tool_input_value": {{"description": "What is the market cap of AMZN?", "expected_output": "The market cap of AMZN"}}}}
    inputs = InputSchema(**inputs)

    response = run(inputs)
    print(response)
"""
    
    return content

def generate_component_yaml(agent_name, user_id):
    component = {
        'name': agent_name,
        'type': agent_name,
        'author': user_id,
        'version': '0.1.0',
        'description': agent_name,
        'license': 'MIT',
        'models': {
            'default_model_provider': 'ollama',
            'ollama': {
                'model': 'ollama/llama3.1:70b',
                'max_tokens': 1000,
                'temperature': 0,
                'api_base': 'http://localhost:11434'
            }
        },
        'inputs': {
            'system_message': 'You are a helpful AI assistant.',
            'save': False,
            'location': 'node'
        },
        'outputs': {
            'filename': 'output.txt',
            'save': False,
            'location': 'node'
        },
        'implementation': {
            'package': {
                'entrypoint': 'run.py'
            }
        }
    }

    with open(f'{AGENT_DIR}/{agent_name}/{agent_name}/component.yaml', 'w') as file:
        yaml.dump(component, file, default_flow_style=False)

def generate_schema(agent_name, params):
    schema_code = '''from pydantic import BaseModel
from typing import Any

class InputSchema(BaseModel):
    tool_name: str
    tool_input_type: str
    tool_input_value: dict
'''

    for name, info in params.items():
        print("INFO", name, info)
        if info['value'] is None:
            if 'List' in str(info['type']):
                schema_code += f'    {name}: list\n'
            elif info['type'] is None:
                schema_code += f'    {name}: Any\n'
            elif issubclass(info["type"], BaseModel):
                schema_code += f'    {name}: dict\n'
            else:
                schema_code += f'    {name}: {info["type"].__name__}\n'
        else:
            if 'List' in str(info['type']):
                schema_code += f'    {name}: list = {info["value"]}\n'
            elif info['type'] is None:
                schema_code += f'    {name}: Any = {info["value"]}\n'
            elif issubclass(info["type"], BaseModel):
                schema_code += f'    {name}: dict = {info["value"]}\n'
            else:
                schema_code += f'    {name}: {info["type"].__name__} = {info["value"]}\n'

    with open(f'{AGENT_DIR}/{agent_name}/{agent_name}/schemas.py', 'w') as file:
        file.write(schema_code)

def git_add_commit(agent_name):
    subprocess.run(["git", "-C", f"{AGENT_DIR}/{agent_name}", "add", "-A"])
    subprocess.run(["git", "-C", f"{AGENT_DIR}/{agent_name}", "commit", "-m", "Initial commit"])
    subprocess.run(["git", "-C", f"{AGENT_DIR}/{agent_name}", "tag", "-f", "v0.1"])

def write_code_to_package(agent_name, code):
    package_path = f'{AGENT_DIR}/{agent_name}'
    code_path = os.path.join(package_path, agent_name, 'run.py')

    os.makedirs(os.path.dirname(code_path), exist_ok=True)
    with open(code_path, 'w') as file:
        file.write(code)

def add_files_to_package(agent_name, params, user_id):
    package_path = f'{AGENT_DIR}/{agent_name}'

    # Generate schema and component yaml
    generate_schema(agent_name, params)
    generate_component_yaml(agent_name, user_id)

    # Create .env.example file
    env_example_path = os.path.join(package_path, '.env.example')
    with open(env_example_path, 'w') as env_file:
        env_file.write('OPENAI_API_KEY=\n')

def zip_dir(directory_path: str) -> None:
    """
    Zip the specified directory and write it to a file on disk.
    """
    output_zip_file = f"{directory_path}.zip"
    with zipfile.ZipFile(output_zip_file, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                file_path = os.path.join(root, file)
                zip_file.write(file_path, os.path.relpath(file_path, directory_path))
    print(f"Zipped directory '{directory_path}' to '{output_zip_file}'")
    return output_zip_file

async def write_to_ipfs(file_path):
    """Write a file to IPFS, optionally publish to IPNS or update an existing IPNS record."""
    try:
        logger.info(f"Writing file to IPFS: {file_path}")
        if not IPFS_GATEWAY_URL:
            return (500, {"message": "IPFS_GATEWAY_URL not found"})
        
        client = ipfshttpclient.connect(IPFS_GATEWAY_URL)
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as tmpfile:
            with open(file_path, "rb") as f:
                content = f.read()            
            tmpfile.write(content)
            tmpfile_name = tmpfile.name
        
        result = client.add(tmpfile_name)
        client.pin.add(result["Hash"])
        os.unlink(tmpfile_name)
        
        ipfs_hash = result["Hash"]
        response = {
            "message": "File written and pinned to IPFS",
            "ipfs_hash": ipfs_hash,
        }

        return (201, response)
    except Exception as e:
        logger.error(f"Error writing file to IPFS: {e}")
        import traceback
        logger.error(f"Error writing file to IPFS: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return (500, {"message": f"Error writing file to IPFS: {e}"})

async def publish_ipfs_package(agent_name, decorator = False):
    package_path = f"{AGENT_DIR}/{agent_name}"

    if not decorator:
        output_zip_file = zip_dir_with_gitignore(Path.cwd())
    else:
        output_zip_file = zip_dir(package_path)
    
    success, response = await write_to_ipfs(output_zip_file)
    logger.info(f"Response: {response}")
    return success, response

# Function to sort modules based on dependencies
def sort_modules(modules, dependencies):
    sorted_modules = []
    unsorted_modules = modules.copy()

    while unsorted_modules:
        for mod in unsorted_modules:
            mod_deps = dependencies[mod['name']]
            if all(dep in [m['name'] for m in sorted_modules] for dep in mod_deps):
                sorted_modules.append(mod)
                unsorted_modules.remove(mod)
                break

    return sorted_modules

# Define a function to extract dependencies from the source code
def extract_dependencies(module, modules):
    dependencies = []
    for mod in modules:
        if mod['name'] != module['name']:
            # Use a negative lookahead to exclude matches within quotes
            pattern = r'\b' + re.escape(mod['name']) + r'\b(?=([^"\']*["\'][^"\']*["\'])*[^"\']*$)'
            if re.search(pattern, module['source']):
                dependencies.append(mod['name'])
    return dependencies

def load_input_schema(repo_name):
    """Loads the input schema"""
    schemas_module = importlib.import_module(f"{repo_name}.schemas")
    input_schema = getattr(schemas_module, "Persona")
    return input_schema

async def load_persona(persona_module):
    """Load persona from a JSON or YAML file in a git repository."""

    hub_username = os.getenv("HUB_USERNAME")
    hub_password = os.getenv("HUB_PASSWORD")
    hub_url = os.getenv("HUB_URL")

    if not hub_username or not hub_password or not hub_url:
        raise ValueError("HUB_USERNAME, HUB_PASSWORD, and HUB_URL environment variables must be set")

    async with Hub(hub_url) as hub:
        success, _, _ = await hub.signin(hub_username, hub_password)
        if not success:
            raise ConnectionError(f"Failed to authenticate with Hub.")            

        personas = await hub.list_personas(persona_module['name'])
    persona = personas[0]
    persona_url = persona['module_url']

    # Clone the repo
    repo_name = persona_url.split('/')[-1]
    repo_path = Path(f"{AGENT_DIR}/{repo_name}")
    
    # Remove existing repo if it exists
    if repo_path.exists():
        import shutil
        shutil.rmtree(repo_path)
        
    _ = Repo.clone_from(persona_url, to_path=str(repo_path))
    
    persona_file = repo_path / persona['module_entrypoint']
    if not persona_file.exists():
        logger.error(f"Persona file not found in repository {repo_name}")
        return None
            
    # Load based on file extension
    with persona_file.open('r') as f:
        if persona_file.suffix == '.json':
            persona_data = json.load(f)
        elif persona_file.suffix in ['.yml', '.yaml']:
            persona_data = yaml.safe_load(f)
        else:
            logger.error(f"Unsupported file type {persona_file.suffix} in {repo_name}")
            return None
        

    # input_schema = load_input_schema(repo_name)
    return persona_data
        
    
    
def read_gitignore(directory):
    gitignore_path = os.path.join(directory, '.gitignore')
    
    if not os.path.exists(gitignore_path):
        logger.info(f"No .gitignore file found in {directory}")
        return []
    
    with open(gitignore_path, 'r') as file:
        lines = file.readlines()

    ignored_files = [line.strip() for line in lines if line.strip() and not line.startswith('#')]
    return ignored_files

def zip_dir_with_gitignore(directory_path):
    ignored_files = read_gitignore(directory_path)
    output_zip_file = f"./{os.path.basename(directory_path)}.zip"

    # Convert patterns in .gitignore to absolute paths for comparison
    ignored_patterns = [os.path.join(directory_path, pattern) for pattern in ignored_files]

    with zipfile.ZipFile(output_zip_file, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for root, dirs, files in os.walk(directory_path):
            dirs = [d for d in dirs if not any(fnmatch.fnmatch(os.path.join(root, d), pattern) for pattern in ignored_patterns)]
            
            for file in files:
                file_path = os.path.join(root, file)

                if any(fnmatch.fnmatch(file_path, pattern) for pattern in ignored_patterns):
                    continue
                
                if file == output_zip_file.split('/')[1]:
                    continue

                zip_file.write(file_path, os.path.relpath(file_path, directory_path))

    logger.info(f"Zipped directory '{directory_path}' to '{output_zip_file}'")
    return output_zip_file
