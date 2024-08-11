import subprocess
import yaml

def create_poetry_package(package_name):
    subprocess.run(["poetry", "new", f"tmp/{package_name}"])


def transform_code_as(input_code):
    # Define the new function signature and logger setup
    new_header = '''from naptha_sdk.utils import get_logger

logger = get_logger(__name__)

def run(inputs, worker_nodes = None, orchestrator_node = None, flow_run = None, cfg: dict = None):'''
    
    # Split the input code into lines
    lines = input_code.strip().split('\n')
    
    # Remove the old function signature
    lines = lines[1:]
    
    # Remove one tab space from each line
    transformed_lines = [line[4:] if line.startswith('    ') else line for line in lines]
    
    # Join the transformed lines with the new header
    transformed_code = new_header + '\n' + '\n'.join(transformed_lines)
    
    return transformed_code

def transform_code_mas(input_code):
    # Define the new function signature and logger setup
    new_header = '''from naptha_sdk.utils import get_logger

logger = get_logger(__name__)

def run(inputs, worker_nodes = None, orchestrator_node = None, flow_run = None, cfg: dict = None):'''
    
    # Split the input code into lines
    lines = input_code.strip().split('\n')
    
    # Remove the old function signature
    lines = lines[1:]
    
    # Remove one tab space from each line
    transformed_lines = [line[4:] if line.startswith('    ') else line for line in lines]
    
    # Join the transformed lines with the new header
    transformed_code = new_header + '\n' + '\n'.join(transformed_lines)
    
    return transformed_code

def generate_component_yaml(module_name, user_id):
    component = {
        'name': module_name,
        'type': module_name,
        'author': user_id,
        'version': '0.1.0',
        'description': module_name,
        'license': 'MIT',
        'models': {
            'default_model_provider': 'ollama',
            'ollama': {
                'model': 'ollama/phi',
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

    with open(f'tmp/{module_name}/{module_name}/component.yaml', 'w') as file:
        yaml.dump(component, file, default_flow_style=False)

def generate_schema(module_name):
    schema_code = '''from pydantic import BaseModel

class InputSchema(BaseModel):
    prompt: str
'''
    with open(f'tmp/{module_name}/{module_name}/schemas.py', 'w') as file:
        file.write(schema_code)

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
    tags = hf_api.list_repo_refs(repo)
    print("Existing tags:", tags)
    tags = [tags.tags[0].name]
    hf_api.delete_tag(repo, tag=tags[-1])
    hf_api.create_tag(repo, repo_type="model", tag="v0.1")
