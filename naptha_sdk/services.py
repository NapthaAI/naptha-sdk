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
        self.node_address = "http://localhost:7001"
        self.payments = Payments(session_key=os.getenv("SESSION_KEY"), environment=Environment.appTesting, version="0.1.0", marketplace_auth_token=os.getenv("MARKETPLACE_AUTH_TOKEN"))
        self.naptha_plan_did = os.getenv("NAPTHA_PLAN_DID")
        self.wallet_address = "0x0106B8532816e6DAdC377697CC58072eD6023075"

    def show_credits(self):
        response = self.payments.get_subscription_balance(self.naptha_plan_did, self.wallet_address)
        print('=========', response.content)

    def get_service_url(self, service_did):
        response = self.payments.get_service_details(service_did)
        print('=========', response)

    def get_service_details(self, service_did):
        response = self.payments.get_service_token(service_did)
        result = json.loads(response.content.decode())
        access_token = result['token']['accessToken']
        proxy_address = result['token']['neverminedProxyUri']
        return access_token, proxy_address

    # def get_nodes(self):
    #     service_did = "did:nv:a9ff0f7a6632c944d277af2c65e7d80e1579239695e1c4e2ff3fd278f4d0e1aa"
    #     response = self.payments.get_asset_ddo(service_did)
    #     result = json.loads(response.content.decode())
    #     service_name = result['service'][0]['attributes']['main']['name']
    #     return {service_name : service_did}

    def get_nodes(self):
        response = self.payments.get_subscription_associated_services("did:nv:98fc642054d5a1a65ea9838bc4bad47ad6a2016e3b7b5ca9b2de693e2ea46d18")
        print('========', response.content)
        # result = json.loads(response.content.decode())
        # service_name = result['service'][0]['attributes']['main']['name']
        # return {service_name : service_did}

    async def run_task(self, task_input):
        self.access_token, self.proxy_address = self.get_service_details(service_did)
        # try:
        async with httpx.AsyncClient() as client:
            # response = await client.post(
            #     f"http://hub.algoverai.link:7001/CreateTask", json=task_input
            # )
            headers = {
                'Content-Type': 'application/json', 
                'Authorization': f'Bearer {self.access_token}',  
            }
            response = await client.post(
                self.proxy_address, 
                json=task_input,
                headers=headers
            )
            if response.status_code != 200:
                print(f"Failed to create task: {response.text}")
        # except Exception as e:
        #     print(f"Exception occurred: {e}")
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
