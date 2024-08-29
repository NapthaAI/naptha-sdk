import os
import re
import subprocess
import tomlkit
from naptha_sdk.config import generate_component_yaml, generate_schema

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
        "branch": "feat/single-file"
    }

    for package in packages:
        dependencies[package] = version

    # Serialize the TOML data and write it back to the file
    with open(f"tmp/{package_name}/pyproject.toml", 'w', encoding='utf-8') as file:
        file.write(tomlkit.dumps(data))

def extract_packages(input_code):
    lines = input_code.strip().split('\n')
    import_pattern = r"\s*from\s+([a-zA-Z_][\w\.]+)\s+import\s+(.*)"
    packages = set()
    for i, line in enumerate(lines):
        # Check if the line starts with 'from' and matches the import pattern
        match = re.match(import_pattern, line)
        if match:
            # Extract the package name from the match
            package_name = match.group(1).strip()
            if not package_name.startswith('naptha_sdk'):
                packages.add(package_name)
    return packages

def transform_code_as(input_code):
    # Define the new function signature and logger setup
    new_header = '''from naptha_sdk.utils import get_logger

logger = get_logger(__name__)

def run(inputs, worker_nodes = None, orchestrator_node = None, flow_run = None, cfg: dict = None):'''
    
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
    transformed_code = new_header + '\n' + '\n'.join(transformed_lines)
    
    return transformed_code

def transform_code_mas(input_code):
    # Define the new function signature and logger setup
    new_header = '''from naptha_sdk.utils import get_logger
from naptha_sdk.agent_service import AgentService

logger = get_logger(__name__)

async def run(inputs, worker_nodes = None, orchestrator_node = None, flow_run = None, cfg: dict = None):'''
    
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
    transformed_code = new_header + '\n' + '\n'.join(transformed_lines)
    
    return transformed_code

def check_hf_repo_exists(hf_api, repo_id: str) -> bool:
    try:
        # This will raise an exception if the repo doesn't exist
        hf_api.repo_info(repo_id)
        return True
    except Exception:
        return False

def publish_hf_package(hf_api, module_name, repo_id, code, user_id):
    with open(f'tmp/{module_name}/{module_name}/run.py', 'w') as file:
        file.write(code)
    generate_schema(module_name)
    generate_component_yaml(module_name, user_id)
    repo = f"{user_id}/{repo_id}"
    if not check_hf_repo_exists(hf_api, repo):
        hf_api.create_repo(repo_id=repo_id)
    hf_api.upload_folder(
        folder_path=f'tmp/{module_name}',
        repo_id=repo,
        repo_type="model",
    )
    tags_info = hf_api.list_repo_refs(repo)
    desired_tag = "v0.1"
    existing_tags = {tag_info.name for tag_info in tags_info.tags} if tags_info.tags else set()
    if desired_tag not in existing_tags:
        hf_api.create_tag(repo, repo_type="model", tag=desired_tag)
    else:
        hf_api.delete_tag(repo, tag=desired_tag)
        hf_api.create_tag(repo, repo_type="model", tag=desired_tag)