import os
import json
import httpx
from httpx import HTTPStatusError
import traceback
import tempfile
import shutil
import zipfile
from pathlib import Path
from typing import Dict, Any, List, Tuple
from naptha_sdk.schemas import ModuleRun, ModuleRunInput
from naptha_sdk.utils import get_logger

logger = get_logger(__name__)


async def check_user_http(node_url: str, user_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check if a user exists on a node
    """
    endpoint = node_url + "/CheckUser"
    try:
        async with httpx.AsyncClient() as client:
            headers = {
                'Content-Type': 'application/json', 
            }
            response = await client.post(
                endpoint, 
                json=user_input,
                headers=headers
            )
            response.raise_for_status()
        return json.loads(response.text)
    except HTTPStatusError as e:
        logger.info(f"HTTP error occurred: {e}")
        raise  
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

async def register_user_http(node_url: str, user_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Register a user on a node
    """
    endpoint = node_url + "/RegisterUser"
    try:
        async with httpx.AsyncClient() as client:
            headers = {
                'Content-Type': 'application/json', 
            }
            response = await client.post(
                endpoint, 
                json=user_input,
                headers=headers
            )
            response.raise_for_status()
        return json.loads(response.text)
    except HTTPStatusError as e:
        logger.info(f"HTTP error occurred: {e}")
        raise  
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

async def run_task_http(node_url: str, module_run_input: Dict[str, Any], access_token: str) -> Dict[str, Any]:
    """
    Run a task on a node
    """
    print("Running module...")
    print(f"Node URL: {node_url}")

    endpoint = node_url + "/CreateTask"
    
    if isinstance(module_run_input, dict):
        task_input = ModuleRunInput(**module_run_input)
    else:
        task_input = module_run_input

    try:
        async with httpx.AsyncClient() as client:
            headers = {
                'Content-Type': 'application/json', 
                'Authorization': f'Bearer {access_token}',  
            }
            response = await client.post(
                endpoint, 
                json=task_input.model_dict(),
                headers=headers
            )
            response.raise_for_status()
        return ModuleRun(**json.loads(response.text))
    except HTTPStatusError as e:
        logger.info(f"HTTP error occurred: {e}")
        raise  
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        error_details = traceback.format_exc()
        print(f"Full traceback: {error_details}")


async def check_tasks_http(node_url: str, ) -> Dict[str, Any]:
    """
    Check the tasks on a node
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{node_url}/CheckTasks"
            )
            response.raise_for_status()
    except HTTPStatusError as e:
        logger.info(f"HTTP error occurred: {e}")
        raise  
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    return json.loads(response.text)


async def check_task_http(node_url: str, module_run: ModuleRun) -> ModuleRun:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{node_url}/CheckTask", json=module_run.model_dict()
            )
            response.raise_for_status()
        return ModuleRun(**json.loads(response.text))
    except HTTPStatusError as e:
        logger.info(f"HTTP error occurred: {e}")
        raise  
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


async def create_task_run_http(node_url: str, module_run_input: ModuleRunInput) -> ModuleRun:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{node_url}/CreateTaskRun", json=module_run_input.model_dict()
            )
            response.raise_for_status()
        return ModuleRun(**json.loads(response.text))
    except HTTPStatusError as e:
        logger.info(f"HTTP error occurred: {e}")
        raise  
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


async def update_task_run_http(node_url: str, module_run: ModuleRun):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{node_url}/UpdateTaskRun", json=module_run.model_dict()
            )
            response.raise_for_status()
        return ModuleRun(**json.loads(response.text))
    except HTTPStatusError as e:
        logger.info(f"HTTP error occurred: {e}")
        raise  
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        error_details = traceback.format_exc()
        print(f"Full traceback: {error_details}")


def zip_directory(file_path, zip_path):
    """Utility function to zip the content of a directory while preserving the folder structure."""
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(file_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, start=os.path.abspath(file_path).split(os.sep)[0])
                zipf.write(file_path, arcname)


def prepare_files(file_path: str) -> List[Tuple[str, str]]:
    """Prepare files for upload."""
    if os.path.isdir(file_path):
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmpfile:
            zip_directory(file_path, tmpfile.name)
            tmpfile.close()  
            file = {'file': open(tmpfile.name, 'rb')}
    else:
        file = {'file': open(file_path, 'rb')}
    
    return file


async def read_storage_http(node_url: str, module_run_id: str, output_dir: str, ipfs: bool = False) -> str:
    print("Reading from storage...")
    try:
        endpoint = f"{node_url}/{'read_ipfs' if ipfs else 'read_storage'}/{module_run_id}"

        async with httpx.AsyncClient(timeout=30.0) as client:  # Increased timeout to 30 seconds
            response = await client.get(endpoint)
            response.raise_for_status()
            storage = response.content  
            print("Retrieved storage.")
        
            # Temporary file handling
            temp_file_name = None
            with tempfile.NamedTemporaryFile(delete=False, mode='wb') as tmp_file:
                tmp_file.write(storage)  # storage is a bytes-like object
                temp_file_name = tmp_file.name
    
            # Ensure output directory exists
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
    
            # Check if the file is a zip file and extract if true
            if zipfile.is_zipfile(temp_file_name):
                with zipfile.ZipFile(temp_file_name, 'r') as zip_ref:
                    zip_ref.extractall(output_path)
                print(f"Extracted storage to {output_dir}.")
            else:
                shutil.copy(temp_file_name, output_path)
                print(f"Copied storage to {output_dir}.")

            # Cleanup temporary file
            Path(temp_file_name).unlink(missing_ok=True)
    
            return output_dir         
    except HTTPStatusError as e:
        logger.info(f"HTTP error occurred: {e}")
        raise  
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


async def write_storage_http(node_url: str, storage_input: str, ipfs: bool = False, publish_to_ipns: bool = False, update_ipns_name: str = None) -> Dict[str, Any]:
    """Write storage to the node."""
    print("Writing storage")
    try:
        file = prepare_files(storage_input)
        endpoint = f"{node_url}/write_ipfs" if ipfs else f"{node_url}/write_storage"
        
        if update_ipns_name:
            publish_to_ipns = True

        data = {
            "publish_to_ipns": publish_to_ipns,
            "update_ipns_name": update_ipns_name
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                endpoint, 
                files=file,
                data=data,
                timeout=600
            )
            response.raise_for_status()
            return response.json()
    except HTTPStatusError as e:
        logger.info(f"HTTP error occurred: {e}")
        raise  
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return {}