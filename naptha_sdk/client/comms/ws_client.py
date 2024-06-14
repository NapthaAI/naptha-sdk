import io
import os
import json
import base64
import zipfile
import traceback
import websockets
import tempfile
from typing import Dict, Any, List, Tuple
from naptha_sdk.schemas import ModuleRun, ModuleRunInput


LOCAL_ID = "node1"


async def relay_message(routing_url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Relay a message to a node via websocket."""
    params['source_node'] = LOCAL_ID
    try:
        async with websockets.connect(routing_url) as websocket:
            await websocket.send(json.dumps(params))
            response = await websocket.recv()
            return json.loads(response)
    except Exception as e:
        print(f"Failed to relay message: {e}")


async def check_user_ws(routing_url: str, indirect_node_id: str, user_input: str) -> Dict[str, Any]:
    """Check a user via websocket."""
    params = {
        'target_node': indirect_node_id,
        'path': 'check_user',
        'params': user_input
    }

    response = await relay_message(routing_url, params)
    print(f"Check user response: {response}")
    return response


async def register_user_ws(routing_url: str, indirect_node_id: str, user_input: str) -> Dict[str, Any]:
    """Register a user via websocket."""
    params = {
        'target_node': indirect_node_id,
        'path': 'register_user',
        'params': user_input
    }

    response = await relay_message(routing_url, params)
    print(f"Register user response: {response}")
    return response


async def run_task_ws(routing_url: str, indirect_node_id: str, module_run_input: ModuleRunInput) -> Dict[str, Any]:
    """Run a task via websocket."""
    print("Running module...")
    print(f"Routing URL: {routing_url}")
    print(f"Indirect node ID: {indirect_node_id}")


    if isinstance(module_run_input, ModuleRun):
        module_run_input = ModuleRunInput(**module_run_input)

    params = {
        'target_node': indirect_node_id,
        'path': 'run_task',
        'params': module_run_input.model_dict()
    }
    try:
        response = await relay_message(routing_url, params)
        print(f"Run task response: {response}")
        return response
    except Exception as e:
            print(f"Exception occurred: {e}")
            error_details = traceback.format_exc()
            print(f"Full traceback: {error_details}")


async def check_task_ws(routing_url: str, indirect_node_id: str, module_run: ModuleRun) -> Dict[str, Any]:
    """Check a task via websocket."""
    params = {
        'target_node': indirect_node_id,
        'path': 'check_task',
        'params': module_run.model_dict()
    }

    response = await relay_message(routing_url, params)
    print(f"Check task response: {response}")
    return response


async def create_task_run_ws(routing_url: str, indirect_node_id: str, module_run_input: ModuleRunInput) -> Dict[str, Any]:
    """Create a task run via websocket."""
    params = {
        'target_node': indirect_node_id,
        'path': 'create_task_run',
        'params': module_run_input.model_dict()
    }

    response = await relay_message(routing_url, params)
    print(f"Create task run response: {response}")
    return response


async def update_task_run_ws(routing_url: str, indirect_node_id: str, module_run: ModuleRun) -> Dict[str, Any]:
    """Update a task run via websocket."""
    params = {
        'target_node': indirect_node_id,
        'path': 'update_task_run',
        'params': module_run.model_dict()
    }

    response = await relay_message(routing_url, params)
    print(f"Update task run response: {response}")
    return json.loads(response)


def decode_file_data(file_data: str, filename: str):
    file_bytes = base64.b64decode(file_data)
    file_stream = io.BytesIO(file_bytes)
    return file_stream


def encode_file_data(file_path: str) -> str:
    """Encode a file to a base64 encoded string."""
    with open(file_path, "rb") as file:
        file_data = file.read()
    return base64.b64encode(file_data).decode('utf-8')


def zip_directory(self, file_path, zip_path):
    """Utility function to zip the content of a directory while preserving the folder structure."""
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(file_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, start=os.path.abspath(file_path).split(os.sep)[0])
                zipf.write(file_path, arcname)


def prepare_files(file_path: str, ipfs: bool = False) -> List[Tuple[str, str]]:
    """Prepare files for upload."""
    if os.path.isdir(file_path):
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmpfile:
            zip_directory(file_path, tmpfile.name)
            tmpfile.close()  
            if ipfs:
                return encode_file_data(tmpfile.name), tmpfile.name
            else:
                return {'file': open(tmpfile.name, 'rb')}, tmpfile.name
    else:
        if ipfs:
            return encode_file_data(file_path), file_path
        else:
            return {'file': open(file_path, 'rb')}, file_path
        

async def read_storage_ws(routing_url: str, indirect_node_id: str, folder_id: str, output_dir: str, ipfs: bool = False) -> Dict[str, Any]:
    """Read storage via websocket."""
    params = {
        'target_node': indirect_node_id,
    }

    if ipfs:
        params['ipfs_hash'] = folder_id
        params['path'] = 'read_from_ipfs'
    else:
        params['folder_id'] = folder_id
        params['path'] = 'read_storage'

    response = await relay_message(routing_url, params)
    file_data = response['params']['file_data']
    file_stream = decode_file_data(file_data, response['params']['filename'])
    with open(os.path.join(output_dir, response['params']['filename']), 'wb') as file:
        file.write(file_stream.read())

    if response['params']['filename'].endswith('.zip'):
        with zipfile.ZipFile(os.path.join(output_dir, response['params']['filename']), 'r') as zip_ref:
            zip_ref.extractall(output_dir)

    return f"{output_dir}/{response['params']['filename']}"


async def write_storage_ws(routing_url: str, indirect_node_id: str, storage_input: str, ipfs: bool = False) -> Dict[str, Any]:
    """Write storage via websocket."""
    file, file_path = prepare_files(storage_input, ipfs)
    params = {
        'target_node': indirect_node_id,
    }

    if ipfs:
        params['path'] = 'write_to_ipfs'
        params['params'] = {
            'file_data': file,
            'filename': file_path
        }
    else:
        params['path'] = 'write_storage'
        params['params'] = {
            'file_data': file,
            'filename': file_path
        }

    response = await relay_message(routing_url, params)
    print(f"Write storage response: {response}")
    return response

