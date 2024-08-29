import os
import re
import subprocess
import tomlkit

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
