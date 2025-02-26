import importlib.util
import ipfshttpclient
import json
from naptha_sdk.client.hub import Hub
from naptha_sdk.utils import get_logger
from git import Repo
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
from naptha_sdk.plugins.manager import PluginManager

logger = get_logger(__name__)

IPFS_GATEWAY_URL = "/dns/provider.akash.pro/tcp/31832/http"
AGENT_DIR = "naptha_modules"

# Initialize plugin system
plugin_manager = PluginManager()
plugin_manager.load_plugins()

def copy_env_file(source_dir, package_name):
    """Copy .env and .pem files from source directory to package directory if they exist"""
    import shutil

    # Copy .env file
    source_env = os.path.join(source_dir, ".env")
    dest_env = os.path.join(AGENT_DIR, package_name, ".env")

    if os.path.exists(source_env):
        shutil.copy2(source_env, dest_env)
        logger.info(f"Copied .env file from {source_env} to {dest_env}")
    else:
        logger.warning(f"No .env file found in {source_dir}")
    
    # Copy .pem file
    source_pem = os.path.join(source_dir, ".pem")
    dest_pem = os.path.join(AGENT_DIR, package_name, ".pem")
    
    if os.path.exists(source_pem):
        shutil.copy2(source_pem, dest_pem)
        logger.info(f"Copied .pem file from {source_pem} to {dest_pem}")
    else:
        logger.warning(f"No .pem file found in {source_dir}")

def copy_configs_directory(source_dir, package_name):
    """Copy the configs directory from source to agent package if it exists."""
    import shutil

    source_configs = os.path.join(source_dir, "configs")
    dest_configs = os.path.join(AGENT_DIR, package_name, "configs")
    if os.path.exists(source_configs) and os.path.isdir(source_configs):
        shutil.copytree(source_configs, dest_configs, dirs_exist_ok=True)
        logger.info(f"Copied configs directory from {source_configs} to {dest_configs}")
    else:
        logger.warning(f"No configs directory found in {source_dir}")

def init_agent_package(package_name):
    """Initialize a new poetry package with proper TOML structure"""
    subprocess.run(["poetry", "new", f"{AGENT_DIR}/{package_name}"])

    # Create initial pyproject.toml with proper structure
    toml_content = tomlkit.document()
    toml_content["build-system"] = {
        "requires": ["poetry-core"],
        "build-backend": "poetry.core.masonry.api",
    }

    toml_content["tool"] = {
        "poetry": {
            "name": package_name,
            "version": "v0.1.0",
            "description": "",
            "authors": [],
            "readme": "README.md",
            "dependencies": {"python": ">=3.10,<3.13"},
        }
    }

    with open(f"{AGENT_DIR}/{package_name}/pyproject.toml", "w", encoding="utf-8") as f:
        f.write(tomlkit.dumps(toml_content))

    # Copy .env file from parent directory
    print(f"parent_dir: {os.getcwd()}")
    copy_env_file(os.getcwd(), package_name)
    copy_configs_directory(os.getcwd(), os.path.join(package_name, package_name))

    subprocess.run(["git", "init", f"{AGENT_DIR}/{package_name}"])

def is_std_lib(module_name):
    try:
        module_spec = importlib.util.find_spec(module_name)
        return module_spec is not None and "site-packages" not in module_spec.origin
    except ImportError:
        return False

def get_parent_project_dependencies():
    """Read dependencies from the parent project's pyproject.toml if it exists"""
    parent_toml_path = os.path.join(os.getcwd(), "pyproject.toml")
    if not os.path.exists(parent_toml_path):
        logger.info("No parent pyproject.toml found")
        return {}
    
    try:
        with open(parent_toml_path, "r", encoding="utf-8") as file:
            parent_data = tomlkit.parse(file.read())
            
        if "tool" in parent_data and "poetry" in parent_data["tool"] and "dependencies" in parent_data["tool"]["poetry"]:
            return parent_data["tool"]["poetry"]["dependencies"]
        return {}
    except Exception as e:
        logger.warning(f"Error reading parent pyproject.toml: {e}")
        return {}

def add_dependencies_to_pyproject(package_name, packages, framework_deps=None):
    """Add dependencies to pyproject.toml using plugin-provided versions"""
    with open(f"{AGENT_DIR}/{package_name}/pyproject.toml", "r", encoding="utf-8") as file:
        data = tomlkit.parse(file.read())

    if "tool" not in data:
        data["tool"] = {"poetry": {"dependencies": {}}}
    elif "poetry" not in data["tool"]:
        data["tool"]["poetry"] = {"dependencies": {}}
    elif "dependencies" not in data["tool"]["poetry"]:
        data["tool"]["poetry"]["dependencies"] = {}

    dependencies = data["tool"]["poetry"]["dependencies"]
    dependencies["python"] = ">=3.10,<3.13"

    # Use plugin-provided dependencies if available
    if framework_deps:
        for pkg, version in framework_deps.items():
            dependencies[pkg] = version

    # Add other standard dependencies
    dependencies["naptha-sdk"] = {
        "git": "https://github.com/NapthaAI/naptha-sdk.git",
        "branch": "plugins",
    }
    dependencies["python-dotenv"] = "*"

    # Copy dependencies from parent project
    parent_deps = get_parent_project_dependencies()
    for pkg, version in parent_deps.items():
        # Skip dependencies we've already added
        if pkg in dependencies:
            continue
        # Skip 'path' dependencies as they're likely local development paths
        if isinstance(version, dict) and "path" in version:
            continue
        # Add the dependency
        dependencies[pkg] = version

    with open(f"{AGENT_DIR}/{package_name}/pyproject.toml", "w", encoding="utf-8") as file:
        file.write(tomlkit.dumps(data))

def parse_deployment_file(deployment_file: str):
    """
    Parse a single deployment.json file, returning a list of dicts
    with the extracted/inferred fields.
    """
    results = []
    try:
        with open(deployment_file, "r") as f:
            data = json.load(f)
        for item in data:
            module_name = item.get("module", {}).get("name", "")
            module_type = item.get("module", {}).get("type", "agent")

            deployment_name = item.get("name", "")

            node_url = item.get("node", {}).get("ip", None)

            config = item.get("config", {})

            load_persona_data = "persona_module" in config

            is_subdeployment = "agent_deployments" in item or "kb_deployments" in item

            user_id = None

            module_run_func_dict = {"agent": "AgentRunInput", "orchestrator": "OrchestratorRunInput"}

            results.append(
                {
                    "module_type": module_type,
                    "function": module_run_func_dict[module_type],
                    "deployment_path": deployment_file,
                    "node_url": node_url,
                    "user_id": user_id,
                    "deployment_name": deployment_name,
                    "load_persona_data": load_persona_data,
                    "is_subdeployment": is_subdeployment,
                }
            )
    except Exception as e:
        print(f"Error parsing {deployment_file}: {e}")
    return results

def get_config_values(config_path):
    configs_to_scan = []
    for root, dirs, files in os.walk(config_path):
        if "deployment.json" in files:
            deployment_path = os.path.join(root, "deployment.json")
            configs_to_scan.append(deployment_path)

    all_results = []
    for path in configs_to_scan:
        results = parse_deployment_file(path)
        all_results.extend(results)

    if not all_results:
        return {}
    return all_results[0]

def render_agent_code(
    agent_name,
    agent_code,
    obj_name,
    local_modules,
    selective_import_modules,
    standard_import_modules,
    variable_modules,
    union_modules,
    params,
    all_imports,
    package_dependencies,
):
    # Log each module type with clear separation and formatting
    logger.info("=== Module Information ===")

    logger.info("\n=== Local Modules ===")
    for module in local_modules:
        logger.info(f"Name: {module.get('name', 'N/A')}\nSource: {module.get('source', 'N/A')}\n")

    logger.info("\n=== Selective Import Modules ===")
    for module in selective_import_modules:
        logger.info(f"Name: {module.get('name', 'N/A')}\nModule: {module.get('module', 'N/A')}\nSource: {module.get('source', 'N/A')}\n")

    logger.info("\n=== Standard Import Modules ===")
    for module in standard_import_modules:
        logger.info(f"Name: {module.get('name', 'N/A')}\n")

    logger.info("\n=== Variable Modules ===")
    for module in variable_modules:
        logger.info(f"Name: {module.get('name', 'N/A')}\nModule: {module.get('module', 'N/A')}\nImport Needed: {module.get('import_needed', False)}\n")

    logger.info("\n=== Union Modules ===")
    for module in union_modules:
        logger.info(f"Source: {module.get('source', 'N/A')}\n")

    logger.info("=== End Module Information ===\n")
    plugin = plugin_manager.detect_framework(all_imports)
    if not plugin:
        raise ValueError(f"No supported framework detected for imports: {all_imports} or dependencies: {package_dependencies}")
    content = ""
    config_values=get_config_values(os.path.abspath("./"))

    # Standard imports
    for module in standard_import_modules:
        content += f'import {module["name"]}\n'

    # Selective imports
    for module in selective_import_modules:
        content += f'from {module["module"]} import {module["name"]}\n'

    # Variable modules
    for module in variable_modules:
        if module["module"] and module["import_needed"]:
            content += f'from {module["module"]} import {module["name"]}\n'

    # Union modules
    for module in union_modules:
        content += module["source"]

    # Core framework imports
    content += textwrap.dedent(f"""\
    from dotenv import load_dotenv
    from typing import Dict
    from naptha_sdk.schemas import *
    from naptha_sdk.user import sign_consumer_id
    from naptha_sdk.utils import get_logger
    from {agent_name}.schemas import InputSchema

    logger = get_logger(__name__)
    load_dotenv()
    """)

    # Add source from selective_import_modules (if any 'source' key exists)
    for module in selective_import_modules:
        if 'source' in module and module['source']:
            content += module['source'] + "\n"
    
    # Add local module sources (like add_numbers_tool)
    for module in local_modules:
        content += module['source'] + "\n\n"

    # Adjust the agent_code text (remove 'self.')
    agent_code = agent_code.replace('self.', '')
    agent_code = agent_code.replace('self', '')
    
    # Preserve original indentation in agent code
    content += textwrap.dedent(agent_code) + "\n\n"

    # Get framework-specific final block
    final_block = plugin.render_agent_code_final_block({
        "agent_name": agent_name,
        "obj_name": obj_name,
        "params": params
    })

    content += final_block
    return content

def generate_schema(agent_name, params):
    schema_code = """from pydantic import BaseModel
from typing import Union, Dict, Any, List, Optional

class InputSchema(BaseModel):
    func_name: str
    input_type: Optional[str] = None
    func_input_data: Optional[Union[Dict[str, Any], List[Dict[str, Any]], str]] = None
"""

    for name, info in params.items():
        print("INFO", name, info)
        if info["value"] is None:
            if "List" in str(info["type"]):
                schema_code += f"    {name}: list\n"
            elif info["type"] is None:
                schema_code += f"    {name}: Any\n"
            elif issubclass(info["type"], BaseModel):
                schema_code += f"    {name}: dict\n"
            else:
                schema_code += f"    {name}: {info['type'].__name__}\n"
        else:
            if "List" in str(info["type"]):
                schema_code += f"    {name}: list = {info['value']}\n"
            elif info["type"] is None:
                schema_code += f"    {name}: Any = {info['value']}\n"
            elif issubclass(info["type"], BaseModel):
                schema_code += f"    {name}: dict = {info['value']}\n"
            else:
                schema_code += f"    {name}: {info['type'].__name__} = {info['value']}\n"

    with open(f"{AGENT_DIR}/{agent_name}/{agent_name}/schemas.py", "w") as file:
        file.write(schema_code)

def git_add_commit(agent_name):
    subprocess.run(["git", "-C", f"{AGENT_DIR}/{agent_name}", "add", "-A"])
    subprocess.run(["git", "-C", f"{AGENT_DIR}/{agent_name}", "commit", "-m", "Initial commit"])
    subprocess.run(["git", "-C", f"{AGENT_DIR}/{agent_name}", "tag", "-f", "v0.1"])

def write_code_to_package(agent_name, code):
    package_path = f"{AGENT_DIR}/{agent_name}"
    code_path = os.path.join(package_path, agent_name, "run.py")

    os.makedirs(os.path.dirname(code_path), exist_ok=True)
    with open(code_path, "w") as file:
        file.write(code)

def add_files_to_package(agent_name, params, user_id):
    package_path = f"{AGENT_DIR}/{agent_name}"

    # Generate schema and component yaml
    generate_schema(agent_name, params)

    # Create .env.example file
    env_example_path = os.path.join(package_path, ".env.example")
    env_content = """PRIVATE_KEY=

OPENAI_API_KEY=
HUB_URL=ws://localhost:3001/rpc
HUB_USERNAME=
HUB_PASSWORD=

NODE_URL=http://localhost:7001"""
    gitignore_path = os.path.join(package_path, ".gitignore")
    with open(env_example_path, "w") as env_file:
        env_file.write(env_content)

    # Create .gitignore file
    gitignore_content = """
# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# C extensions
*.so

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# PyInstaller
#  Usually these files are written by a python script from a template
#  before PyInstaller builds the exe, so as to inject date/other infos into it.
*.manifest
*.spec

# Installer logs
pip-log.txt
pip-delete-this-directory.txt

# Unit test / coverage reports
htmlcov/
.tox/
.nox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.py,cover
.hypothesis/
.pytest_cache/
cover/

# Translations
*.mo
*.pot

# Django stuff:
*.log
local_settings.py
db.sqlite3
db.sqlite3-journal

# Flask stuff:
instance/
.webassets-cache

# Scrapy stuff:
.scrapy

# Sphinx documentation
docs/_build/

# PyBuilder
.pybuilder/
target/

# Jupyter Notebook
.ipynb_checkpoints

# IPython
profile_default/
ipython_config.py

# pyenv
# .python-version

# pipenv
#Pipfile.lock

# poetry
#poetry.lock

# pdm
#.pdm.toml
#.pdm-python
#.pdm-build/

# Celery stuff
celerybeat-schedule
celerybeat.pid

# SageMath parsed files
*.sage.py

# Environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# Spyder project settings
.spyderproject
.spyproject

# Rope project settings
.ropeproject

# mkdocs documentation
/site

# mypy
.mypy_cache/
.dmypy.json
dmypy.json

# Pyre type checker
.pyre/

# pytype static type analyzer
.pytype/

# Cython debug symbols
cython_debug/
"""
    with open(gitignore_path, "w") as gitignore_file:
        gitignore_file.write(gitignore_content)

def create_env_file():
    env_path = ".env"
    env_content = '''OPENAI_API_KEY=
NODE_URL=http://localhost:7001
# NODE_URL=https://node.naptha.ai

PRIVATE_KEY=
HUB_URL=ws://localhost:3001/rpc
# HUB_URL=wss://hub.naptha.ai/rpc
HUB_USERNAME=
HUB_PASSWORD='''
    with open(env_path, 'w') as env_file:
        env_file.write(env_content)

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

async def publish_ipfs_package(agent_name, decorator=False):
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
            mod_deps = dependencies[mod["name"]]
            if all(dep in [m["name"] for m in sorted_modules] for dep in mod_deps):
                sorted_modules.append(mod)
                unsorted_modules.remove(mod)
                break

    return sorted_modules

# Define a function to extract dependencies from the source code
def extract_dependencies(module, modules):
    dependencies = []
    for mod in modules:
        if mod["name"] != module["name"]:
            # Use a negative lookahead to exclude matches within quotes
            pattern = r"\b" + re.escape(mod["name"]) + r"\b(?=([^\"']*[\"'][^\"']*[\"'])*[^\"']*$)"
            if re.search(pattern, module["source"]):
                dependencies.append(mod["name"])
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

        personas = await hub.list_personas(persona_module["name"])
    persona = personas[0]
    persona_url = persona["module_url"]

    # Clone the repo
    repo_name = persona_url.split("/")[-1]
    repo_path = Path(f"{AGENT_DIR}/{repo_name}")

    # Remove existing repo if it exists
    if (repo_path).exists():
        import shutil

        shutil.rmtree(repo_path)

    _ = Repo.clone_from(persona_url, to_path=str(repo_path))

    persona_file = repo_path / persona["module_entrypoint"]
    if not persona_file.exists():
        logger.error(f"Persona file not found in repository {repo_name}")
        return None

    # Load based on file extension
    with persona_file.open("r") as f:
        if persona_file.suffix == ".json":
            persona_data = json.load(f)
        elif persona_file.suffix in [".yml", ".yaml"]:
            persona_data = yaml.safe_load(f)
        else:
            logger.error(f"Unsupported file type {persona_file.suffix} in {repo_name}")
            return None

    return persona_data

def read_gitignore(directory):
    gitignore_path = os.path.join(directory, ".gitignore")

    if not os.path.exists(gitignore_path):
        logger.info(f"No .gitignore file found in {directory}")
        return []

    with open(gitignore_path, "r") as file:
        lines = file.readlines()

    ignored_files = [line.strip() for line in lines if line.strip() and not line.startswith("#")]
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

                if file == output_zip_file.split("/")[1]:
                    continue

                zip_file.write(file_path, os.path.relpath(file_path, directory_path))

    logger.info(f"Zipped directory '{directory_path}' to '{output_zip_file}'")
    return output_zip_file