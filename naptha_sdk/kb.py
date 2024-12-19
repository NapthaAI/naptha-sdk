from naptha_sdk.client.node import Node
from naptha_sdk.schemas import KBDeployment, KBRunInput, KBRun
from typing import Any, Dict, List, Union
import logging

logger = logging.getLogger(__name__)

class KnowledgeBase:
    def __init__(self, kb_deployment: KBDeployment):
        self.kb_deployment = kb_deployment
        self.kb_node = Node(self.kb_deployment.kb_node_url)
        self.table_name = kb_deployment.kb_config['table_name']
        self.schema = kb_deployment.kb_config['schema']
        if "id_column" in kb_deployment.kb_config:
            self.id_column = kb_deployment.kb_config['id_column']
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

    async def upsert_kb(self, id_: str, data: Dict[str, Any]):
        try:
            # check if the id_ exists
            existing_data = await self.kb_node.query_table(
                self.table_name,
                condition={self.id_column: id_}
            )

            if existing_data["rows"]:
                # update existing record
                await self.kb_node.update_row(
                    self.table_name,
                    data=data,
                    condition={self.id_column: id_}
                )
                logger.info(f"Updated knowledge base with id: {id_}")
            else:
                # insert new record
                await self.kb_node.add_row(
                    self.table_name,
                    data={self.id_column: id_, **data}
                )
                logger.info(f"Inserted new knowledge base with id: {id_}")
        except Exception as e:
            logger.error(f"Error upserting knowledge base: {str(e)}")
            raise
    
    async def get_kb(self, column_name: str, column_value: str) -> Dict[str, Any]:
        try:
            data = await self.kb_node.query_table(
                self.table_name,
                condition={column_name: column_value}
            )
            return data["rows"][0] if data["rows"] else None
        except Exception as e:
            logger.error(f"Error getting knowledge base: {str(e)}")
            raise
        
    async def call_kb_func(self, kb_run_input: KBRunInput):
        logger.info(f"Running knowledge base on knowledge base node {self.kb_node.node_url}")
        kb_run = await self.kb_node.run_kb_and_poll(kb_run_input)
        return kb_run
