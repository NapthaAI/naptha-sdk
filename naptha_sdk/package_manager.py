import io
import ipfshttpclient
from naptha_sdk.utils import get_logger
import os
import re
import shutil
import subprocess
import tempfile
import tomlkit
import yaml
import zipfile

logger = get_logger(__name__)

IPFS_GATEWAY_URL="/dns/provider.akash.pro/tcp/31832/http"

def create_poetry_package(package_name):
    subprocess.run(["poetry", "new", f"tmp/{package_name}"])

def add_dependency_to_pyproject(package_name, packages, version="*", dev=False):
    with open(f"tmp/{package_name}/pyproject.toml", 'r', encoding='utf-8') as file:
        data = tomlkit.parse(file.read())

    # Access the correct dependencies section
    dep_key = 'dev-dependencies' if dev else 'dependencies'
    dependencies = data['tool']['poetry'][dep_key]

    dependencies["naptha-sdk"] = {
        "git": "https://github.com/NapthaAI/naptha-sdk.git",
        "branch": "feat/agent-decorator"
    }

    for package in packages:
        dependencies[package] = version

    # Serialize the TOML data and write it back to the file
    with open(f"tmp/{package_name}/pyproject.toml", 'w', encoding='utf-8') as file:
        file.write(tomlkit.dumps(data))

def render_agent_code(agent_name, input_code, local_modules, installed_modules):
    # Add the imports for installed modules (e.g. crewai)
    content = ''
    for module in installed_modules:
        line = f'from {module['module']} import {module['name']} \n'
        content += line

    # Add the naptha imports and logger setup
    naptha_imports = f'''from {agent_name}.schemas import InputSchema
from naptha_sdk.utils import get_logger

logger = get_logger(__name__)

'''
    content += naptha_imports

    # Add the source code for the local modules 
    for module in local_modules:
        content += module['source'] + "\n"

    # Define the new function signature
    content += 'def run(inputs: InputSchema, *args, **kwargs): \n'
    
    # Split the input code into lines
    lines = input_code.strip().split('\n')
    
    def_line_index = 0  # Initialize the index to find where the function definition starts

    # Find the index of the line that starts with 'def' or 'async def'
    for i, line in enumerate(lines):
        stripped_line = line.strip()
        if stripped_line.startswith('def ') or stripped_line.startswith('async def'):
            def_line_index = i
            break
    
    # Remove all lines up to and including the line that contains the 'def'
    lines = lines[def_line_index + 1:]

    # Remove one tab space from each line
    transformed_lines = [line[4:] if line.startswith('    ') else line for line in lines]
    
    # Join the transformed lines with the new header
    rendered_code = content + '\n' + '\n'.join(transformed_lines)
    
    return rendered_code

import yaml

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

    with open(f'tmp/{agent_name}/{agent_name}/component.yaml', 'w') as file:
        yaml.dump(component, file, default_flow_style=False)

def generate_schema(agent_name):
    schema_code = '''from pydantic import BaseModel

class InputSchema(BaseModel):
    prompt: str
'''
    with open(f'tmp/{agent_name}/{agent_name}/schemas.py', 'w') as file:
        file.write(schema_code)

def add_files_to_package(agent_name, code, user_id):

    # Define paths
    package_path = f'tmp/{agent_name}'
    code_path = os.path.join(package_path, agent_name, 'run.py')

    # Clean up if directory exists
    if os.path.exists(package_path):
        shutil.rmtree(package_path)

    # Write the provided code to the specified path
    os.makedirs(os.path.dirname(code_path), exist_ok=True)
    with open(code_path, 'w') as file:
        file.write(code)

    # Generate schema and component yaml (you should provide these functions)
    generate_schema(agent_name)
    generate_component_yaml(agent_name, user_id)

    return package_path

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
            return (500, {"message": "IPFS_GATEWAY_URL not found in environment"})
        
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
        return (500, {"message": f"Error writing file to IPFS: {e}"})

async def publish_ipfs_package(package_path):
    output_zip_file = zip_dir(package_path)
    success, response = await write_to_ipfs(output_zip_file)
    logger.info(f"Response: {response}")
    return success, response

