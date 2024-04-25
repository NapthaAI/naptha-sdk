import asyncio
from dotenv import load_dotenv
import os
import tempfile
import tarfile
import json
from pathlib import Path
from payments_py import Payments, Environment
from typing import Dict, List, Tuple, Optional
import httpx
import zipfile

load_dotenv()

class Services:
    def __init__(self):
        self.node_address = os.getenv("NODE_ENDPOINT")
        self.payments = Payments(session_key=os.getenv("SESSION_KEY"), environment=Environment.appTesting, version="0.1.0", marketplace_auth_token=os.getenv("MARKETPLACE_AUTH_TOKEN"))
        self.naptha_plan_did = os.getenv("NAPTHA_PLAN_DID")
        self.wallet_address = os.getenv("WALLET_ADDRESS") 

    def show_credits(self):
        response = self.payments.get_subscription_balance(self.naptha_plan_did, self.wallet_address)
        creds = json.loads(response.content.decode())["balance"]
        print('Credits: ', creds)
        return creds

    def get_service_url(self, service_did):
        response = self.payments.get_service_details(service_did)
        print('Service URL: ', response)
        return response

    def get_service_details(self, service_did):
        response = self.payments.get_service_token(service_did)
        result = json.loads(response.content.decode())
        access_token = result['token']['accessToken']
        proxy_address = result['token']['neverminedProxyUri']
        return access_token, proxy_address

    def get_asset_ddo(self, service_did):
        response = self.payments.get_asset_ddo(service_did)
        result = json.loads(response.content.decode())
        service_name = result['service'][0]['attributes']['main']['name']
        return service_name

    def list_services(self):
        response = self.payments.get_subscription_associated_services(self.naptha_plan_did)
        service_dids = json.loads(response.content.decode())
        service_names = []
        for did in service_dids:
            service_names.append(self.get_asset_ddo(did))
        print('Services: ', service_names)
        return service_names

    async def run_task(self, task_input, local):
        if local:
            self.access_token, self.proxy_address = None, self.node_address
        else:
            self.access_token, self.proxy_address = self.get_service_details(service_did)
        print("Running module...")
        print(f"Node address: {self.node_address}")
        endpoint = self.proxy_address + "/CreateTask"
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    'Content-Type': 'application/json', 
                    'Authorization': f'Bearer {self.access_token}',  
                }
                response = await client.post(
                    endpoint, 
                    json=task_input,
                    headers=headers
                )
                if response.status_code != 200:
                    print(f"Failed to create task: {response.text}")
        except Exception as e:
            print(f"Exception occurred: {e}")
        return json.loads(response.text)

    async def check_tasks(self):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.proxy_address}/CheckTasks"
                )
                if response.status_code != 200:
                    print(f"Failed to check task: {response.text}")
        except Exception as e:
            print(f"Exception occurred: {e}")
        return json.loads(response.text)

    async def check_task(self, job):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.node_address}/CheckTask", json=job
                )
                if response.status_code != 200:
                    print(f"Failed to check task: {response.text}")
            return json.loads(response.text)
        except Exception as e:
            print(f"Exception occurred: {e}")

    async def read_storage(self, job_id, output_dir, local, ipfs=False):
        """Read from storage."""
        if local:
            self.access_token, self.node_address = None, self.node_address
        else:
            self.access_token, self.node_address = self.get_service_details(service_did)
        print("Reading from storage...")
        print(f"Node address: {self.node_address}")
        try:
            if ipfs:
                endpoint = f"{self.node_address}/read_ipfs/{job_id}"
            else:
                endpoint = f"{self.node_address}/read_storage/{job_id}"
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    endpoint
                )

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

    def prepare_files(self, files: List[str]) -> List[Tuple[str, str]]:
        """Prepare files for upload."""
        print(f"Preparing files: {files}")
        files = [Path(file) for file in files]
        f = []
        for path in files:
            if path.is_dir():
                for file_path in path.rglob('*'):
                    if file_path.is_file():
                        relative_path = file_path.relative_to(path.parent)
                        f.append(('file', (relative_path.as_posix(), open(file_path, 'rb'))))
            elif path.is_file():
                f.append(('file', (path.name, open(path, 'rb'))))
        return f
    
    async def write_storage(self, storage_input: List[str], ipfs: bool = False) -> Dict[str, str]:
        """Write storage to the node."""
        print("Writing storage")
        try:
            if ipfs:
                endpoint = f"{self.node_address}/write_ipfs"
            else:
                files = self.prepare_files(storage_input)
                endpoint = f"{self.node_address}/write_storage"
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    endpoint, 
                    files=files
                )
                if response.status_code != 201:
                    print(f"Failed to write storage: {response.text}")
        except Exception as e:
            print(f"Exception occurred: {e}")
        return json.loads(response.text)