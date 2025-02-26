import logging
from naptha_sdk.client.node import NodeClient, UserClient
from naptha_sdk.schemas import KBDeployment, KBRunInput
from naptha_sdk.schemas import SecretInput
from typing import List

logger = logging.getLogger(__name__)

class KnowledgeBase:
    async def create(self, deployment: KBDeployment, *args, **kwargs):
        logger.info(f"Creating knowledge base on worker node {deployment.node}")
        node = UserClient(deployment.node)
        kb_deployment = await node.create(module_type="kb", module_request=deployment)
        return kb_deployment

    async def run(self, module_run_input: KBRunInput, secrets: List[SecretInput] = [], *args, **kwargs):
        logger.info(f"Running knowledge base on worker node {module_run_input.deployment.node}")
        node = NodeClient(module_run_input.deployment.node)
        kb_run = await node.run_module(module_type="kb", run_input=module_run_input, secrets=secrets)
        return kb_run
