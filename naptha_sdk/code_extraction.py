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
            'save': 'false',
            'location': 'node'
        },
        'outputs': {
            'filename': 'output.txt',
            'save': 'false',
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
