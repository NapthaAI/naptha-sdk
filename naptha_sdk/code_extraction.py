import subprocess

def create_poetry_package(package_name):
    subprocess.run(["poetry", "new", package_name])


def transform_code(input_code):
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