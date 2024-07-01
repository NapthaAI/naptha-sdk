import io
import os
import uuid
import json
import base64
import shutil
import zipfile
import traceback
import tempfile
from typing import Dict, Any, List, Tuple
import websockets
from naptha_sdk.schemas import ModuleRun, ModuleRunInput
from naptha_sdk.utils import get_logger

logger = get_logger(__name__)
LOCAL_ID = str(uuid.uuid4())
CHUNK_SIZE = 256 * 1024

# Utility functions
def decode_file_data(file_data: str, filename: str):
    """Decode base64 encoded file data."""
    file_bytes = base64.b64decode(file_data)
    return io.BytesIO(file_bytes)

def encode_file_data(file_path: str) -> str:
    """Encode a file to a base64 encoded string."""
    with open(file_path, "rb") as file:
        file_data = file.read()
    return base64.b64encode(file_data).decode('utf-8')

def zip_directory(directory_path: str, zip_path: str):
    """Zip the content of a directory."""
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                file_full_path = os.path.join(root, file)
                arcname = os.path.relpath(file_full_path, start=directory_path)
                zipf.write(file_full_path, arcname)

def prepare_files(file_path: str, ipfs: bool = False) -> List[Tuple[str, str]]:
    """Prepare files for upload."""
    if os.path.isdir(file_path):
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmpfile:
            zip_directory(file_path, tmpfile.name)
            tmpfile.close()
        return encode_file_data(tmpfile.name), tmpfile.name
    else:
        return encode_file_data(file_path), file_path

async def relay_message(routing_url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Relay a message to a node via websocket."""
    params['source_node'] = LOCAL_ID
    routing_path = f"{routing_url}/ws/{LOCAL_ID}"
    try:
        async with websockets.connect(routing_path) as websocket:
            await websocket.send(json.dumps(params))
            response = await websocket.recv()
            return json.loads(response)['params']
    except Exception as e:
        logger.error(f"Failed to relay message: {e}")
        return {"error": str(e)}

async def send_file(websocket, file_path: str, filename: str, target_node: str, ipfs: bool = False):
    """Send a file via websocket."""
    file_size = os.path.getsize(file_path)
    chunk_index = 0

    with open(file_path, "rb") as file:
        while chunk := file.read(CHUNK_SIZE):
            encoded_chunk = base64.b64encode(chunk).decode('utf-8')
            params = {
                'source_node': LOCAL_ID,
                'target_node': target_node,
                'path': 'write_storage' if not ipfs else 'write_to_ipfs',
                'params': {
                    'filename': filename,
                    'file_data': encoded_chunk,
                    'chunk_index': chunk_index,
                    'chunk_total': (file_size // CHUNK_SIZE) + 1
                }
            }
            await websocket.send(json.dumps(params))
            logger.info(f"Sent chunk {chunk_index + 1} of {params['params']['chunk_total']}")
            chunk_index += 1

    eof_params = {
        'source_node': LOCAL_ID,
        'target_node': target_node,
        'path': 'write_storage' if not ipfs else 'write_to_ipfs',
        'params': {
            'filename': filename,
            'file_data': 'EOF',
            'chunk_index': chunk_index,
            'chunk_total': (file_size // CHUNK_SIZE) + 1
        }
    }
    await websocket.send(json.dumps(eof_params))
    logger.info("EOF sent")

# WebSocket interaction functions
async def check_user_ws(routing_url: str, indirect_node_id: str, user_input: Dict[str, Any]) -> Dict[str, Any]:
    """Check a user via websocket."""
    params = {
        'target_node': indirect_node_id,
        'path': 'check_user',
        'params': user_input
    }
    logger.info(f"Check user params: {params}")
    response = await relay_message(routing_url, params)
    logger.info(f"Check user response: {response}")
    return response

async def register_user_ws(routing_url: str, indirect_node_id: str, user_input: Dict[str, Any]) -> Dict[str, Any]:
    """Register a user via websocket."""
    params = {
        'target_node': indirect_node_id,
        'path': 'register_user',
        'params': user_input
    }
    response = await relay_message(routing_url, params)
    logger.info(f"Register user response: {response}")
    return response

async def run_task_ws(routing_url: str, indirect_node_id: str, module_run_input: ModuleRunInput) -> Dict[str, Any]:
    """Run a task via websocket."""
    logger.info("Running module...")
    logger.info(f"Routing URL: {routing_url}")
    logger.info(f"Indirect node ID: {indirect_node_id}")

    if isinstance(module_run_input, ModuleRun):
        module_run_input = ModuleRunInput(**module_run_input).model_dict()

    params = {
        'target_node': indirect_node_id,
        'path': 'create_task',
        'params': module_run_input
    }
    try:
        response = await relay_message(routing_url, params)
        logger.info(f"Run task response: {response}")
        return response
    except Exception as e:
        logger.error(f"Exception occurred: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return {"error": str(e)}

async def check_task_ws(routing_url: str, indirect_node_id: str, module_run: ModuleRun) -> Dict[str, Any]:
    """Check a task via websocket."""
    params = {
        'target_node': indirect_node_id,
        'path': 'check_task',
        'params': module_run.model_dict()
    }
    response = await relay_message(routing_url, params)
    logger.info(f"Check task response: {response}")
    return response

async def create_task_run_ws(routing_url: str, indirect_node_id: str, module_run_input: ModuleRunInput) -> Dict[str, Any]:
    """Create a task run via websocket."""
    params = {
        'target_node': indirect_node_id,
        'path': 'create_task_run',
        'params': module_run_input.model_dict()
    }
    response = await relay_message(routing_url, params)
    logger.info(f"Create task run response: {response}")
    return response

async def update_task_run_ws(routing_url: str, indirect_node_id: str, module_run: ModuleRun) -> Dict[str, Any]:
    """Update a task run via websocket."""
    params = {
        'target_node': indirect_node_id,
        'path': 'update_task_run',
        'params': module_run.model_dict()
    }
    response = await relay_message(routing_url, params)
    logger.info(f"Update task run response: {response}")
    return response

async def read_storage_ws(routing_url: str, indirect_node_id: str, folder_id: str, output_dir: str, ipfs: bool = False) -> str:
    """Read storage via websocket."""
    params = {
        'target_node': indirect_node_id,
        'source_node': LOCAL_ID,
        'params': {'ipfs_hash': folder_id} if ipfs else {'folder_id': folder_id},
        'path': 'read_from_ipfs' if ipfs else 'read_storage'
    }

    logger.info(f"Reading storage with params: {params}")
    logger.info(f"Output directory: {output_dir}")

    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_zip_path = temp_file.name
        accumulate_chunks = io.BytesIO()

        async with websockets.connect(f"{routing_url}/ws/{LOCAL_ID}") as websocket:
            await websocket.send(json.dumps(params))
            while True:
                try:
                    response = await websocket.recv()
                    response_data = json.loads(response)['params']
                    filename = response_data['filename']
                    file_data = response_data['file_data']
                    logger.info(f"Received chunk {response_data['chunk_index']} of {response_data['chunk_total']}")
                    if file_data == 'EOF':
                        break
                    chunk = base64.b64decode(file_data)
                    accumulate_chunks.write(chunk)
                except websockets.ConnectionClosed:
                    logger.info("WebSocket connection closed")
                    break

        logger.info(f"Writing received data to temporary file: {temp_zip_path}")
        with open(temp_zip_path, 'wb') as file:
            file.write(accumulate_chunks.getvalue())

        if filename.endswith('.zip'):
            logger.info(f"Extracting zip file {filename} to {output_dir}")
            with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                zip_ref.extractall(output_dir)
        else:
            logger.info(f"Moving file {filename} to {output_dir}")
            final_path = os.path.join(output_dir, os.path.basename(filename))
            os.makedirs(os.path.dirname(final_path), exist_ok=True)
            shutil.move(temp_zip_path, final_path)
            logger.info(f"File moved to {final_path}")

    return output_dir

async def write_storage_ws(routing_url: str, indirect_node_id: str, storage_input: str, ipfs: bool = False) -> Dict[str, Any]:
    """Write storage via websocket."""
    if os.path.isdir(storage_input):
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmpfile:
            zip_directory(storage_input, tmpfile.name)
            tmpfile.close()
            file_path = tmpfile.name
            filename = os.path.basename(file_path)
    else:
        file_path = storage_input
        filename = os.path.basename(file_path)

    async with websockets.connect(f"{routing_url}/ws/{LOCAL_ID}", ping_interval=None) as websocket:
        await send_file(websocket, file_path, filename, indirect_node_id, ipfs)
        while True:
            try:
                response = await websocket.recv()
                response_data = json.loads(response)['params']
                logger.info(f"Response: {response_data}")
                if 'message' in response_data or 'error' in response_data:
                    break
            except websockets.ConnectionClosed:
                logger.info("WebSocket connection closed")
                break