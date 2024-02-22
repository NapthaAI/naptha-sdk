import asyncio
import os
# import jwt
import json
from typing import Dict, List, Tuple
import httpx
import logging
from pathlib import Path


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger


logger = get_logger(__name__)


class Coworker:
    def __init__(self, username: str, password: str, node_address: str):
        self.username = username
        self.password = password
        self.node_address = node_address

    async def run_task(self, task_input: Dict[str, str]):
        """Run a task on the node."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.node_address}/CreateTask", json=task_input
                )
                if response.status_code != 200:
                    logger.error(f"Failed to run task: {response.text}")
        except Exception as e:
            logger.error(f"Exception occurred: {e}")
        return json.loads(response.text)

    async def check_tasks(self):
        """Check the status of all tasks."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.node_address}/CheckTasks"
                )
                if response.status_code != 200:
                    logger.error(f"Failed to check task: {response.text}")
        except Exception as e:
            logger.error(f"Exception occurred: {e}")
        return json.loads(response.text)

    async def check_task(self, job: Dict[str, str]):
        """Check the status of a task."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.node_address}/CheckTask", json=job
                )
                if response.status_code != 200:
                    logger.error(f"Failed to check task: {response.text}")
        except Exception as e:
            logger.error(f"Exception occurred: {e}")
        return json.loads(response.text)
    
    def prepare_files(self, files: List[str]) -> List[Tuple[str, str]]:
        """Prepare files for upload."""
        logger.debug(f"Preparing files: {files}")
        files = [Path(file) for file in files]
        f = []
        for path in files:
            if path.is_dir():
                for file_path in path.rglob('*'):
                    if file_path.is_file():
                        relative_path = file_path.relative_to(path.parent)
                        f.append(('files', (relative_path.as_posix(), open(file_path, 'rb'))))
            elif path.is_file():
                f.append(('files', (path.name, open(path, 'rb'))))
        return f
    
    async def write_storage(self, storage_input: List[str]) -> Dict[str, str]:
        """Write storage to the node."""
        files = self.prepare_files(storage_input)
        logger.debug(f"Writing storage: {files}")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.node_address}/WriteStorage", 
                    files=files
                )
                if response.status_code != 201:
                    logger.error(f"Failed to write storage: {response.text}")
        except Exception as e:
            logger.error(f"Exception occurred: {e}")
        return json.loads(response.text)
    
    async def read_storage(self, job_id: str):
        """Get storage from the node."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.node_address}/GetStorage/{job_id}"
                )
                if response.status_code != 200:
                    logger.error(f"Failed to get storage: {response.text}")
        except Exception as e:
            logger.error(f"Exception occurred: {e}")

        return response
