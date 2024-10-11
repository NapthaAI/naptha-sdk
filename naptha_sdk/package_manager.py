import importlib.util
import ipfshttpclient
from naptha_sdk.utils import get_logger
import os
import re
import subprocess
import tempfile
import textwrap
import time
import tomlkit
import yaml
import zipfile

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

def render_agent_code(agent_name, agent_code, obj_name, local_modules, selective_import_modules, standard_import_modules, variable_modules):
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

    # Add the naptha imports and logger setup
    naptha_imports = f'''from dotenv import load_dotenv
from {agent_name}.schemas import InputSchema
from naptha_sdk.utils import get_logger

logger = get_logger(__name__)

load_dotenv()

'''
    content += naptha_imports


    # Add the source code for the local modules 
    for module in local_modules:
        content += module['source'] + "\n"

    for module in variable_modules:
        content += module['source'] + "\n"

    # Convert class method to function
    agent_code = agent_code.replace('self.', '')
    agent_code = agent_code.replace('self', '')

    content += textwrap.dedent(agent_code) + "\n\n"

    # Define the new function signature
    content += f"""def run(inputs: InputSchema, *args, **kwargs):
    {agent_name}_0 = {obj_name}()

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

def generate_schema(agent_name):
    schema_code = '''from pydantic import BaseModel

class InputSchema(BaseModel):
    tool_name: str
    tool_input_type: str
    tool_input_value: dict
'''

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

def add_files_to_package(agent_name, user_id):
    package_path = f'{AGENT_DIR}/{agent_name}'

    # Generate schema and component yaml
    generate_schema(agent_name)
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

async def publish_ipfs_package(agent_name):
    package_path = f"{AGENT_DIR}/{agent_name}"
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