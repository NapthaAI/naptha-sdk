from naptha_sdk.client.node import NodeClient
from naptha_sdk.schemas import KBDeployment, KBRunInput
from typing import Any, Dict
import logging
logger = logging.getLogger(__name__)

class KnowledgeBase:
    def __init__(self, kb_deployment: KBDeployment):
        self.kb_deployment = kb_deployment
        self.kb_node = NodeClient(self.kb_deployment.node)
        self.table_name = kb_deployment.config.path
        self.schema = kb_deployment.config.schema
        if "id_column" in kb_deployment.config:
            self.id_column = kb_deployment.config.id_column
        else:
            self.id_column = "id"
        if self.table_name is None:
            self.table_name = kb_deployment.module["name"]

    @classmethod
    async def create(cls, module_run):
        instance = cls(module_run)
        await instance._initialize()
        return instance

    async def _initialize(self):
        try:
            tables = await self.kb_node.list_tables()
            if self.table_name not in tables:
                await self.kb_node.create_table(self.table_name, self.schema)
        except Exception as e:
            logger.error(f"Error initializing knowledge base: {str(e)}")
            raise
        
    async def call_kb_func(self, module_run_input: KBRunInput, *args, **kwargs):
        logger.info(f"Running knowledge base on knowledge base node {self.kb_node}")
        kb_run = await self.kb_node.run_module(module_type="kb", run_input=module_run_input.model_dict())
        return kb_run
