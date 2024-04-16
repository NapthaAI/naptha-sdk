import asyncio
from dotenv import load_dotenv
import os
import json
from payments_py import Payments, Environment
from typing import Dict, List, Tuple, Optional
import httpx

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
