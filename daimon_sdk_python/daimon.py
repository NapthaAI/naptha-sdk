import asyncio
import os
# import jwt
import json
from typing import Dict, List, Tuple, Optional
import httpx


class Daimon:
    """The Daimon class is the entry point into NapthaAI Daimon."""

    def __init__(self, username, password, node_address):
        self.username = username
        self.password = password
        self.node_address = node_address

    async def run_task(self, job):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.node_address}/CreateTask", json=job
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
                    f"{self.node_address}/CheckTasks"
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
        except Exception as e:
            print(f"Exception occurred: {e}")
        return json.loads(response.text)
