import asyncio
from dotenv import load_dotenv
import inspect
import json
import os
import time
from pathlib import Path
import shutil

import tomlkit
from naptha_sdk.client.hub import Hub
from naptha_sdk.client.node import UserClient
from naptha_sdk.configs import setup_module_deployment
from naptha_sdk.inference import InferenceClient
from naptha_sdk.module_manager import AGENT_DIR, add_files_to_package, add_dependencies_to_pyproject, git_add_commit, \
    init_agent_package, render_agent_code, write_code_to_package, publish_ipfs_package
from naptha_sdk.schemas import User
from naptha_sdk.scrape import scrape_init, scrape_func, scrape_func_params
from naptha_sdk.user import get_public_key
from naptha_sdk.utils import get_logger, url_to_node
import httpx
import subprocess
import re

logger = get_logger(__name__)

load_dotenv(override=True)

class Naptha:
    """The entry point into Naptha."""

    def __init__(self):
        self.public_key = get_public_key(os.getenv("PRIVATE_KEY")) if os.getenv("PRIVATE_KEY") else None
        self.user = User(id=f"user:{self.public_key}")
        self.hub_username = os.getenv("HUB_USERNAME", None)
        self.hub_url = os.getenv("HUB_URL", None)

        node_url = os.getenv("NODE_URL")

        if node_url is None:
            raise ValueError("NODE_URL is not set. Make sure your project has a .env file with a NODE_URL variable.")

        self.node = UserClient(url_to_node(node_url))
        self.inference_client = InferenceClient(url_to_node(node_url))
        self.hub = Hub(self.hub_url, self.public_key)  

    async def __aenter__(self):
        """Async enter method for context manager"""
        await self.hub.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async exit method for context manager"""
        await self.hub.close()

    async def create_agent(self, name, module_url):
        async with self.hub:
            _, _, user_id = await self.hub.signin(self.hub_username, os.getenv("HUB_PASSWORD"))
            agent_config = {
                "id": f"agent:{name}",
                "name": name,
                "description": name,
                "author": self.hub.user_id,
                "module_url": module_url,  # Use the provided IPFS URL
                "module_type": "agent",
                "module_version": "v0.1",
                "execution_type": "package",
                "module_entrypoint": "run.py",
                "parameters": "",
            }
            logger.info(f"Registering Agent {agent_config}")
            agent = await self.hub.create_or_update_module("agent", agent_config)
            if agent:
                logger.info(f"Agent {name} created successfully")
            else:
                logger.error(f"Failed to create agent {name}")

    async def publish_modules(self, decorator=False, register=None, subdeployments=False, github=False):
        logger.info(f"Publishing Agent Packages...")
        start_time = time.time()

        if decorator and github:
            raise ValueError("GitHub publishing is not supported when using decorators.")

        if not decorator:
            module_path = Path.cwd()
            deployment_path = module_path / module_path.name / "configs" / "deployment.json"
            with open(deployment_path, "r", encoding="utf-8") as f:
                deployment = json.load(f)
            module = deployment[0]["module"]
            if "module_type" not in module:
                module["module_type"] = "agent"
            modules = [module]
            if subdeployments:
                deployment = await setup_module_deployment(module['module_type'], deployment_path)
                for module_type in ['agent', 'kb', 'tool', 'environment']:
                    subdeployment = module_type + '_deployments'
                    if hasattr(deployment, subdeployment) and getattr(deployment, subdeployment):
                        for submodule in getattr(deployment, subdeployment):
                            modules.append(submodule.module)
        else:
            path = Path.cwd() / AGENT_DIR
            dir_items = [item.name for item in path.iterdir() if item.is_dir()]
            modules = []
            for mod_item in dir_items:
                git_add_commit(mod_item)
                mod_data = {
                    "name": mod_item,
                    "description": mod_item,
                    "parameters": "",
                    "module_type": "agent",
                    "module_url": "None",
                    "module_version": "v0.1",
                    "module_entrypoint": "run.py",
                    "execution_type": "package"
                }
                modules.append(mod_data)

        if github:
            # Check for GITHUB_TOKEN
            secrets = await self.hub.list_secrets()
            github_token = next((s['secret_value'] for s in secrets if s['key_name'] == 'GITHUB_TOKEN'), None)
            if not github_token:
                github_token = os.getenv('GITHUB_TOKEN')
            if not github_token:
                raise ValueError("GITHUB_TOKEN is required for publishing to GitHub. Please set it as a secret or environment variable.")

            # Read pyproject.toml
            with open('pyproject.toml', 'r') as f:
                pyproject = tomlkit.load(f)
            if 'project' not in pyproject or 'name' not in pyproject['project'] or 'version' not in pyproject['project']:
                raise ValueError("pyproject.toml is missing required fields: project.name and project.version")
            name = pyproject['project']['name']
            version = pyproject['project']['version']

            # Create GitHub repository with proper timeout settings and retry logic
            try:
                # Use a longer timeout for GitHub API calls
                async with httpx.AsyncClient(timeout=120.0) as client:  # Increased timeout to 120 seconds
                    # First get the authenticated user's information
                    try:
                        user_response = await client.get(
                            'https://api.github.com/user',
                            headers={'Authorization': f'token {github_token}'}
                        )
                        user_response.raise_for_status()
                        owner = user_response.json()['login']
                    except httpx.TimeoutException:
                        logger.error("Timeout while getting GitHub user information. Falling back to IPFS.")
                        for module in modules:
                            if isinstance(register, str):
                                continue
                            _, response = await publish_ipfs_package(module["name"], decorator)
                            module['module_url'] = f"ipfs://{response['ipfs_hash']}"
                        return  # Skip GitHub publishing
                    except httpx.HTTPError as e:
                        logger.error(f"Error accessing GitHub API: {str(e)}. Falling back to IPFS.")
                        for module in modules:
                            if isinstance(register, str):
                                continue
                            _, response = await publish_ipfs_package(module["name"], decorator)
                            module['module_url'] = f"ipfs://{response['ipfs_hash']}"
                        return  # Skip GitHub publishing
                    
                    # Check if repository already exists
                    repo_exists = False
                    try:
                        repo_response = await client.get(
                            f'https://api.github.com/repos/{owner}/{name}',
                            headers={'Authorization': f'token {github_token}'}
                        )
                        if repo_response.status_code == 200:
                            repo_data = repo_response.json()
                            repo_exists = True
                            logger.info(f"Using existing GitHub repository: {repo_data['html_url']}")
                    except httpx.HTTPStatusError:
                        # Repository doesn't exist
                        pass
                    except httpx.TimeoutException:
                        logger.error("Timeout checking GitHub repository existence. Falling back to IPFS.")
                        for module in modules:
                            if isinstance(register, str):
                                continue
                            _, response = await publish_ipfs_package(module["name"], decorator)
                            module['module_url'] = f"ipfs://{response['ipfs_hash']}"
                        return  # Skip GitHub publishing
                    
                    if not repo_exists:
                        # Create new repository with retry logic
                        max_retries = 3
                        retry_delay = 2  # seconds
                        
                        for retry in range(max_retries):
                            try:
                                response = await client.post(
                                    'https://api.github.com/user/repos',
                                    headers={'Authorization': f'token {github_token}'},
                                    json={'name': name, 'private': False}
                                )
                                response.raise_for_status()
                                repo_data = response.json()
                                logger.info(f"Created new GitHub repository: {repo_data['html_url']}")
                                break
                            except httpx.TimeoutException:
                                if retry < max_retries - 1:
                                    logger.warning(f"Timeout creating repository. Retrying in {retry_delay} seconds...")
                                    await asyncio.sleep(retry_delay)
                                    retry_delay *= 2  # Exponential backoff
                                else:
                                    logger.error("Failed to create GitHub repository after retries. Falling back to IPFS.")
                                    for module in modules:
                                        if isinstance(register, str):
                                            continue
                                        _, response = await publish_ipfs_package(module["name"], decorator)
                                        module['module_url'] = f"ipfs://{response['ipfs_hash']}"
                                    return  # Skip GitHub publishing
                            except httpx.HTTPError as e:
                                if retry < max_retries - 1:
                                    logger.warning(f"HTTP error creating repository: {e}. Retrying in {retry_delay} seconds...")
                                    await asyncio.sleep(retry_delay)
                                    retry_delay *= 2  # Exponential backoff
                                else:
                                    logger.error(f"Failed to create GitHub repository after retries: {e}. Falling back to IPFS.")
                                    for module in modules:
                                        if isinstance(register, str):
                                            continue
                                        _, response = await publish_ipfs_package(module["name"], decorator)
                                        module['module_url'] = f"ipfs://{response['ipfs_hash']}"
                                    return  # Skip GitHub publishing
                    
                    repo_url = repo_data['html_url']
                    repo_clone_url = repo_data['clone_url']

                    # Create authenticated URL for Git operations
                    # Extract the https://github.com part and add token
                    auth_url = re.sub(r'https://', f'https://{github_token}@', repo_clone_url)

                    # Check if we're in a git repository
                    is_git_repo = False
                    try:
                        await asyncio.to_thread(
                            subprocess.run, ['git', 'rev-parse', '--is-inside-work-tree'],
                            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
                        )
                        is_git_repo = True
                    except subprocess.CalledProcessError:
                        # Not a git repo, initialize it
                        logger.info("Initializing git repository...")
                        await asyncio.to_thread(
                            subprocess.run, ['git', 'init'], check=True
                        )

                    # FIRST: Find large files BEFORE any git operations
                    large_files = []
                    for root, dirs, files in os.walk('.'):
                        # Skip .git directory
                        if '.git' in dirs:
                            dirs.remove('.git')
                        
                        for file in files:
                            file_path = os.path.join(root, file)
                            if os.path.isfile(file_path):
                                size_mb = os.path.getsize(file_path) / (1024 * 1024)
                                if size_mb > 95:  # Using 95MB as threshold to be safe
                                    large_files.append((file_path, size_mb))
                    
                    # Handle large files BEFORE git operations
                    if large_files:
                        logger.warning(f"Found {len(large_files)} large files that exceed GitHub's 100MB limit:")
                        for file_path, size_mb in large_files:
                            logger.warning(f"  {file_path}: {size_mb:.2f} MB")
                        
                        # Create backup directory for large files
                        large_files_dir = Path(".large_files_backup")
                        large_files_dir.mkdir(exist_ok=True)
                        
                        # Create or update .gitignore
                        with open(".gitignore", "a+") as gitignore:
                            gitignore.seek(0)
                            content = gitignore.read()
                            gitignore.seek(0, 2)  # Go to end of file
                            
                            # Add .large_files_backup directory to gitignore if not already there
                            if ".large_files_backup/" not in content:
                                gitignore.write("\n# Large files backup directory\n.large_files_backup/\n")
                            
                            # Add specific large files to gitignore
                            for file_path, _ in large_files:
                                rel_path = os.path.relpath(file_path, '.')
                                if rel_path not in content:
                                    gitignore.write(f"{rel_path}\n")
                                    logger.info(f"Added {rel_path} to .gitignore")
                                
                                # Move large file to backup directory
                                backup_path = large_files_dir / os.path.basename(file_path)
                                try:
                                    shutil.copy2(file_path, backup_path)
                                    logger.info(f"Backed up {file_path} to {backup_path}")
                                except Exception as e:
                                    logger.error(f"Failed to backup {file_path}: {str(e)}")

                        # Publish large files to IPFS
                        logger.info("Publishing large files to IPFS instead of GitHub...")
                        for module in modules:
                            if isinstance(register, str):
                                continue
                            _, response = await publish_ipfs_package(module["name"], decorator)
                            module['module_url'] = f"ipfs://{response['ipfs_hash']}"
                    
                    # Check if there are any commits
                    has_commits = False
                    try:
                        result = await asyncio.to_thread(
                            subprocess.run, ['git', 'rev-parse', '--verify', 'HEAD'],
                            check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE
                        )
                        has_commits = result.returncode == 0
                    except Exception:
                        has_commits = False

                    if not has_commits:
                        # Set up initial branch and make first commit
                        logger.info("No commits found. Setting up initial branch and commit...")
                        
                        # Configure git user if not already configured
                        await asyncio.to_thread(
                            subprocess.run, ['git', 'config', 'user.email', 'noreply@naptha.io'],
                            check=False
                        )
                        await asyncio.to_thread(
                            subprocess.run, ['git', 'config', 'user.name', 'Naptha CLI'],
                            check=False
                        )
                        
                        # Create main branch - try main first, fallback to master if needed
                        try:
                            await asyncio.to_thread(
                                subprocess.run, ['git', 'checkout', '-b', 'main'],
                                check=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE
                            )
                            current_branch = "main"
                        except subprocess.CalledProcessError:
                            # If main branch creation fails, try master
                            await asyncio.to_thread(
                                subprocess.run, ['git', 'checkout', '-b', 'master'],
                                check=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE
                            )
                            current_branch = "master"
                        
                        # Add all files and make initial commit
                        await asyncio.to_thread(
                            subprocess.run, ['git', 'add', '.'],
                            check=True
                        )
                        await asyncio.to_thread(
                            subprocess.run, ['git', 'commit', '-m', 'Initial commit'],
                            check=True
                        )
                    else:
                        # Get current branch name only if we have commits
                        try:
                            current_branch = await asyncio.to_thread(
                                subprocess.check_output, ['git', 'rev-parse', '--abbrev-ref', 'HEAD'], text=True
                            )
                            current_branch = current_branch.strip()
                        except subprocess.CalledProcessError:
                            # If we can't determine branch name, try main, then fall back to master
                            try:
                                await asyncio.to_thread(
                                    subprocess.check_output, ['git', 'show-ref', '--verify', '--quiet', 'refs/heads/main'], 
                                    stderr=subprocess.STDOUT
                                )
                                current_branch = "main"
                            except subprocess.CalledProcessError:
                                current_branch = "master"
                            logger.info(f"Could not determine branch name, using: {current_branch}")

                    # Check if remote 'origin' already exists and update or add it with authenticated URL
                    try:
                        remotes = await asyncio.to_thread(
                            subprocess.check_output, ['git', 'remote'], text=True
                        )
                        remotes = remotes.strip().split('\n') if remotes.strip() else []
                        
                        if 'origin' in remotes:
                            # Update the existing remote with authenticated URL
                            await asyncio.to_thread(
                                subprocess.run, ['git', 'remote', 'set-url', 'origin', auth_url], check=True
                            )
                        else:
                            # Add new remote with authenticated URL
                            await asyncio.to_thread(
                                subprocess.run, ['git', 'remote', 'add', 'origin', auth_url], check=True
                            )
                    except subprocess.CalledProcessError:
                        # If error, try adding the remote without checking
                        await asyncio.to_thread(
                            subprocess.run, ['git', 'remote', 'add', 'origin', auth_url], check=False
                        )

                    # Push code to GitHub with the authenticated URL
                    # Only attempt push if we haven't already decided to use IPFS for large files
                    if not large_files:
                        try:
                            logger.info(f"Pushing to branch: {current_branch}")
                            await asyncio.to_thread(
                                subprocess.run, ['git', 'push', '-u', 'origin', current_branch], check=True
                            )
                        except subprocess.CalledProcessError as e:
                            error_output = str(e)
                            if "remote: error: File" in error_output and "exceeds GitHub's file size limit" in error_output:
                                # Extract file names from error message
                                file_pattern = r"remote: error: File ([^\s]+) is ([0-9.]+) MB"
                                matches = re.findall(file_pattern, error_output)
                                
                                logger.error("GitHub push failed due to large files detected during push.")
                                if matches:
                                    logger.warning("Large files detected from error message:")
                                    for file_path, size in matches:
                                        logger.warning(f"  {file_path}: {size} MB")
                                    
                                    # Create .gitignore file or append to it
                                    with open(".gitignore", "a+") as gitignore:
                                        gitignore.seek(0)
                                        content = gitignore.read()
                                        gitignore.seek(0, 2)  # Go to end of file
                                        
                                        for file_path, _ in matches:
                                            if file_path not in content:
                                                gitignore.write(f"\n{file_path}\n")
                                                logger.info(f"Added {file_path} to .gitignore")
                                    
                                    # Remove large files from git index
                                    for file_path, _ in matches:
                                        await asyncio.to_thread(
                                            subprocess.run, ['git', 'rm', '--cached', file_path], check=False
                                        )
                                    
                                    # Commit changes to gitignore
                                    await asyncio.to_thread(
                                        subprocess.run, ['git', 'add', '.gitignore'], check=True
                                    )
                                    await asyncio.to_thread(
                                        subprocess.run, ['git', 'commit', '-m', 'Exclude large files from git'], check=True
                                    )
                                    
                                    # Try pushing again
                                    try:
                                        logger.info("Pushing again after excluding large files...")
                                        await asyncio.to_thread(
                                            subprocess.run, ['git', 'push', '-u', 'origin', current_branch, '--force'], check=True
                                        )
                                    except subprocess.CalledProcessError:
                                        logger.error("Push still failed after excluding large files. Falling back to IPFS.")
                                        for module in modules:
                                            if isinstance(register, str):
                                                continue
                                            _, response = await publish_ipfs_package(module["name"], decorator)
                                            module['module_url'] = f"ipfs://{response['ipfs_hash']}"
                                else:
                                    # Fallback to IPFS if we can't parse the error
                                    logger.error("Falling back to IPFS for module publication")
                                    for module in modules:
                                        if isinstance(register, str):
                                            continue
                                        _, response = await publish_ipfs_package(module["name"], decorator)
                                        module['module_url'] = f"ipfs://{response['ipfs_hash']}"
                            else:
                                # Handle other errors
                                logger.error(f"Failed to push to GitHub: {str(e)}")
                                logger.info("Falling back to IPFS for module publication")
                                for module in modules:
                                    if isinstance(register, str):
                                        continue
                                    _, response = await publish_ipfs_package(module["name"], decorator)
                                    module['module_url'] = f"ipfs://{response['ipfs_hash']}"

                    # Only attempt tag and release operations if we've successfully pushed to GitHub
                    if not large_files:
                        # Create and push tag based on module version
                        for module in modules:
                            try:
                                module_version = module.get("module_version", "v0.1")
                                # Create git tag
                                logger.info(f"Creating git tag: {module_version}")
                                
                                # Check if tag already exists before creating it
                                tag_exists = False
                                try:
                                    await asyncio.to_thread(
                                        subprocess.run, ['git', 'show-ref', '--tags', f'refs/tags/{module_version}'],
                                        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
                                    )
                                    tag_exists = True
                                    logger.info(f"Tag {module_version} already exists, skipping tag creation")
                                except subprocess.CalledProcessError:
                                    # Tag doesn't exist, we can create it
                                    pass
                                    
                                if not tag_exists:
                                    await asyncio.to_thread(
                                        subprocess.run, ['git', 'tag', '-a', module_version, '-m', f"Release {module_version}"],
                                        check=True
                                    )
                                
                                # Push the tag to remote
                                logger.info(f"Pushing git tag: {module_version}")
                                await asyncio.to_thread(
                                    subprocess.run, ['git', 'push', 'origin', module_version],
                                    check=False  # Don't raise error if tag already exists on remote
                                )
                                
                                # Continue with the rest of the code...
                                
                                # Create GitHub release using the API
                                logger.info(f"Creating GitHub release for tag: {module_version}")
                                release_data = {
                                    "tag_name": module_version,
                                    "name": f"Release {module_version}",
                                    "body": f"Release notes for {module['name']} version {module_version}"
                                }
                                
                                release_response = await client.post(
                                    f'https://api.github.com/repos/{owner}/{name}/releases',
                                    headers={
                                        'Authorization': f'token {github_token}',
                                        'Accept': 'application/vnd.github+json'
                                    },
                                    json=release_data
                                )
                                
                                if release_response.status_code in (201, 200):
                                    release_info = release_response.json()
                                    logger.info(f"GitHub release created successfully: {release_info.get('html_url')}")
                                else:
                                    logger.error(f"Failed to create GitHub release. Status: {release_response.status_code}, Response: {release_response.text}")
                            except subprocess.CalledProcessError as e:
                                logger.error(f"Failed to create or push git tag: {str(e)}")
                            except httpx.HTTPError as e:
                                logger.error(f"Failed to create GitHub release: {str(e)}")
                            except Exception as e:
                                logger.error(f"Unexpected error during tag/release creation: {str(e)}")
                                
                        # Use clean URL (without token) for module config
                        if not isinstance(register, str):
                            # Check if we had to fall back to IPFS (module_url already set)
                            if 'module_url' not in modules[0] or not modules[0]['module_url'].startswith('ipfs://'):
                                modules[0]['module_url'] = repo_clone_url
            except Exception as e:
                logger.error(f"Unexpected error during GitHub operations: {str(e)}")
                logger.info("Falling back to IPFS for module publication")
                for module in modules:
                    if isinstance(register, str):
                        continue
                    _, response = await publish_ipfs_package(module["name"], decorator)
                    module['module_url'] = f"ipfs://{response['ipfs_hash']}"

        if register:
            await self.hub.signin(self.hub_username, os.getenv("HUB_PASSWORD"))

        for module in modules:
            if isinstance(register, str):
                module_url = register
                logger.info(f"Using provided URL for {module['module_type']} {module['name']}: {module_url}")
            elif 'module_url' in module and module['module_url'] != "None":
                module_url = module['module_url']
            else:
                # Publish to IPFS
                _, response = await publish_ipfs_package(module["name"], decorator)
                module_url = f"ipfs://{response['ipfs_hash']}"
                logger.info(f"Storing {module['name']} on IPFS")
                logger.info(f"Module URL: {module_url}")
                logger.info(f"IPFS Hash: {response['ipfs_hash']}. You can download it from http://ipfs-gateway.naptha.work/ipfs/{response['ipfs_hash']}")

            if register:
                # Register module with hub
                module_config = {
                    "id": f"{module['module_type']}:{module['name']}",
                    "name": module["name"],
                    "description": module.get("description", "No description provided"),
                    "parameters": module.get("parameters", ""),
                    "author": self.hub.user_id,
                    "module_url": module_url,
                    "module_type": module["module_type"],
                    "module_version": module.get("module_version", "v0.1"),
                    "module_entrypoint": module.get("module_entrypoint", "run.py"),
                    "execution_type": module.get("execution_type", "package"),
                }
                logger.info(f"Registering {module['module_type']} {module['name']} on Naptha Hub {module_config}")
                await self.hub.create_or_update_module(module['module_type'], module_config)

        end_time = time.time()
        total_time = end_time - start_time
        logger.info(f"Total time taken to publish {len(modules)} modules: {total_time:.2f} seconds")

    def build(self):
        asyncio.run(self.build_agents())

    async def connect_publish(self):
        await self.hub.connect()
        await self.hub.signin(os.getenv("HUB_USERNAME"), os.getenv("HUB_PASSWORD"))
        await self.publish_agents()
        await self.hub.close()

    async def connect_user_secret(self, key_name):
        await self.hub.connect()
        await self.hub.signin(os.getenv("HUB_USERNAME"), os.getenv("HUB_PASSWORD"))
        result = await self.hub.get_user_secret(key_name)
        await self.hub.close()

        return result

    def publish(self):
        asyncio.run(self.connect_publish())

    def get_user_secret(self, key_name: str) -> str:
        result = asyncio.run(self.connect_user_secret(key_name))
        return result[0]['secret_value'] if len(result) > 0 else []


def agent(name):
    def decorator(func):
        frame = inspect.currentframe()
        package_dependencies = {}
        caller_frame = frame.f_back
        instantiation_file = caller_frame.f_code.co_filename
        variables = scrape_init(instantiation_file)
        
        # Parse pyproject.toml to get package dependencies
        pyproject_path = Path(os.path.join(Path.cwd() / AGENT_DIR, name, "pyproject.toml"))
        if pyproject_path.exists():
            with open(pyproject_path, "r", encoding="utf-8") as f:
                toml_data = tomlkit.load(f)
            if "project" in toml_data and "dependencies" in toml_data["project"]:
                deps = toml_data["project"]["dependencies"]
                for dep in deps:
                    if "@" in dep:
                        pkg, url = dep.split("@", 1)
                        package_dependencies[pkg.strip()] = {"git": url.strip()}
                    else:
                        match = re.match(r"(\w+)(.*)", dep)
                        if match:
                            pkg, version = match.groups()
                            package_dependencies[pkg] = version.strip() if version else "*"
        else:
            logger.warning(f"pyproject.toml not found at {pyproject_path}")        
        
        params = scrape_func_params(func)
        agent_code, obj_name, local_modules, selective_import_modules, standard_import_modules, variable_modules, union_modules = scrape_func(func, variables)
                
        # Collect all imports for framework detection
        all_imports = (
            [mod["module"] for mod in selective_import_modules if "module" in mod]
            + [mod["name"] for mod in standard_import_modules]
        )
        agent_code = render_agent_code(name, agent_code, obj_name, local_modules, selective_import_modules, standard_import_modules, variable_modules, union_modules, params, all_imports, package_dependencies)
        init_agent_package(name)
        write_code_to_package(name, agent_code)
        add_dependencies_to_pyproject(name, selective_import_modules + standard_import_modules)
        add_files_to_package(name, params, os.getenv("HUB_USERNAME"))

        return func
    return decorator

class Agent:
    def __init__(self, 
        name, 
        fn, 
        agent_node_url, 
    ):
        self.name = name
        self.fn = fn
        self.agent_node_url = agent_node_url
        self.repo_id = name