import yaml

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

    with open(f'tmp/{module_name}/{module_name}/component.yaml', 'w') as file:
        yaml.dump(component, file, default_flow_style=False)

def generate_schema(module_name):
    schema_code = '''from pydantic import BaseModel

class InputSchema(BaseModel):
    prompt: str
'''
    with open(f'tmp/{module_name}/{module_name}/schemas.py', 'w') as file:
        file.write(schema_code)