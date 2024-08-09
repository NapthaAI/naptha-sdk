import asyncio
from datetime import datetime
import json
from naptha_sdk.client.node import Node
from naptha_sdk.utils import get_logger
import os
import pytz
import requests
import time
import traceback

logger = get_logger(__name__)

async def run_mas(multi_agent_service, mas_run) -> None:
    mas_engine = MASEngine(multi_agent_service, mas_run)
    await mas_engine.start_run()


class MASEngine:
    def __init__(self, multi_agent_service, mas_run):
        self.mas = multi_agent_service
        self.mas_run = mas_run
        self.mas_name = multi_agent_service.module_name
        self.parameters = mas_run.module_params
        self.orchestrator_node = Node(self.mas_run.orchestrator_node)
        logger.info(f"Orchestrator node: {self.orchestrator_node.node_url}")

        if mas_run.worker_nodes is not None:
            self.worker_nodes = [Node(worker_node) for worker_node in mas_run.worker_nodes]
        else:
            self.worker_nodes = None

        logger.info(f"Worker Nodes: {self.worker_nodes}")

        self.consumer = {
            "public_key": mas_run.consumer_id.split(':')[1],
            'id': mas_run.consumer_id,
        }

    async def start_run(self):
        logger.info(f"Starting MAS run: {self.mas_run}")
        logger.info(f"Checking user: {self.consumer}")
        consumer = await self.orchestrator_node.check_user(user_input=self.consumer)
        if consumer["is_registered"] == True:
            logger.info("Found user...", consumer)
        elif consumer["is_registered"] == False:
            logger.info("No user found. Registering user...")
            consumer = await self.orchestrator_node.register_user(user_input=consumer)
            logger.info(f"User registered: {consumer}.")

        logger.info(f"Running multi agent service on orchestrator node {self.orchestrator_node.node_url}: {self.mas_run}")
        mas_run = await self.orchestrator_node.run_task(module_run_input=self.mas_run)
        logger.info(f"Created multi agent service run on orchestrator node {self.orchestrator_node.node_url}: {mas_run}")

        while True:
            mas_run = await self.orchestrator_node.check_task(mas_run)
            logger.info(mas_run.status)  

            if mas_run.status in ["completed", "error"]:
                break
            time.sleep(3)

        if mas_run.status == 'completed':
            logger.info(mas_run.results)
            self.agent_service_result = mas_run.results
            return mas_run.results
        else:
            logger.info(mas_run.error_message)
            return mas_run.error_message

