import httpx
import json
from naptha_sdk.schemas import ModuleRun, ModuleRunInput
import os
from pathlib import Path
import shutil
import tempfile
import traceback
from typing import Dict, List, Tuple
import zipfile

class Node:
    def __init__(self, node_url):
        self.node_url = node_url
        self.access_token = None

    async def check_user(self, user_input):
        print(f"Checking user: {user_input}")
        endpoint = self.node_url + "/CheckUser"
        async with httpx.AsyncClient() as client:
            headers = {
                'Content-Type': 'application/json', 
            }
            response = await client.post(
                endpoint, 
                json=user_input,
                headers=headers
            )
            if response.status_code != 200:
                print(f"Failed to check user: {response.text}")
        return json.loads(response.text)

    async def register_user(self, user_input):
        print(f"Registering user: {user_input}")
        endpoint = self.node_url + "/RegisterUser"
        async with httpx.AsyncClient() as client:
            headers = {
                'Content-Type': 'application/json', 
            }
            response = await client.post(
                endpoint, 
                json=user_input,
                headers=headers
            )
            if response.status_code != 200:
                print(f"Failed to register user: {response.text}")
        return json.loads(response.text)

    async def run_task(self, module_run_input: ModuleRunInput) -> ModuleRun:
        print("Running module...")
        print(f"Node URL: {self.node_url}")

        if isinstance(module_run_input, dict):
            module_run_input = ModuleRunInput(**module_run_input)

        endpoint = self.node_url + "/CreateTask"
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    'Content-Type': 'application/json', 
                    'Authorization': f'Bearer {self.access_token}',  
                }
                response = await client.post(
                    endpoint, 
                    json=module_run_input.model_dict(),
                    headers=headers
                )
                if response.status_code != 200:
                    print(f"Failed to create task: {response.text}")
            return ModuleRun(**json.loads(response.text))
        except Exception as e:
            print(f"Exception occurred: {e}")
            error_details = traceback.format_exc()
            print(f"Full traceback: {error_details}")

    async def check_tasks(self):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.node_url}/CheckTasks"
                )
                if response.status_code != 200:
                    print(f"Failed to check task: {response.text}")
        except Exception as e:
            print(f"Exception occurred: {e}")
        return json.loads(response.text)

    async def check_task(self, module_run: ModuleRun) -> ModuleRun:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.node_url}/CheckTask", json=module_run.model_dict()
                )
                if response.status_code != 200:
                    print(f"Failed to check task: {response.text}")
            return ModuleRun(**json.loads(response.text))
        except Exception as e:
            print(f"Exception occurred: {e}")

    async def create_task_run(self, module_run_input: ModuleRunInput) -> ModuleRun:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.node_url}/CreateTaskRun", json=module_run_input.model_dict()
                )
                if response.status_code != 200:
                    print(f"Failed to create task run: {response.text}")
            return ModuleRun(**json.loads(response.text))
        except Exception as e:
            print(f"Exception occurred: {e}")

    async def update_task_run(self, module_run: ModuleRun):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.node_url}/UpdateTaskRun", json=module_run.model_dict()
                )
                if response.status_code != 200:
                    print(f"Failed to update task run: {response.text}")
            return ModuleRun(**json.loads(response.text))
        except Exception as e:
            print(f"Exception occurred: {e}")
            error_details = traceback.format_exc()
            print(f"Full traceback: {error_details}")

    async def read_storage(self, module_run_id, output_dir, ipfs=False):
        print("Reading from storage...")
        try:
            endpoint = f"{self.node_url}/{'read_ipfs' if ipfs else 'read_storage'}/{module_run_id}"

            async with httpx.AsyncClient(timeout=30.0) as client:  # Increased timeout to 30 seconds
                response = await client.get(endpoint)
                if response.status_code == 200:
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
                else:
                    print("Failed to retrieve storage.")            
        except Exception as err:
            print(f"Error: {err}")  

    def zip_directory(self, file_path, zip_path):
        """Utility function to zip the content of a directory while preserving the folder structure."""
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(file_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, start=os.path.abspath(file_path).split(os.sep)[0])
                    zipf.write(file_path, arcname)

    def prepare_files(self, file_path: str) -> List[Tuple[str, str]]:
        """Prepare files for upload."""
        if os.path.isdir(file_path):
            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmpfile:
                self.zip_directory(file_path, tmpfile.name)
                tmpfile.close()  
                file = {'file': open(tmpfile.name, 'rb')}
        else:
            file = {'file': open(file_path, 'rb')}
        
        return file
    
    async def write_storage(self, storage_input: str, ipfs: bool = False) -> Dict[str, str]:
        """Write storage to the node."""
        print("Writing storage")
        try:
            file = self.prepare_files(storage_input)
            if ipfs:
                endpoint = f"{self.node_url}/write_ipfs"
            else:
                files = self.prepare_files(storage_input)
                endpoint = f"{self.node_url}/write_storage"
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    endpoint, 
                    files=file
                )
                if response.status_code != 201:
                    print(f"Failed to write storage: {response.text}")
        except Exception as e:
            print(f"Exception occurred: {e}")
        return json.loads(response.text)