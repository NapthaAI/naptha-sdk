from naptha_sdk.client.node import Node
from naptha_sdk.schemas import AgentRun, EnvironmentDeployment, EnvironmentRunInput, OrchestratorRun
from typing import Any, Dict, List, Union
import logging

logger = logging.getLogger(__name__)

class Environment:
    def __init__(self, environment_deployment: EnvironmentDeployment):
        self.environment_deployment = environment_deployment
        self.environment_node = Node(self.environment_deployment.environment_node_url)
        self.table_name = "multi_chat_simulations"

    @classmethod
    async def create(cls, module_run):
        """Factory method to create and initialize an Environment instance."""
        instance = cls(module_run)
        await instance._initialize()
        return instance

    async def _initialize(self):
        """Initialize the environment by creating the table."""
        try:
            # First try to query if table exists
            tables = await self.environment_node.list_tables()
            print(f"Tables: {tables}")
            if self.table_name not in tables:
                schema = {
                    "run_id": {"type": "text", "primary_key": True},
                    "messages": {"type": "jsonb"}  
                }
                await self.environment_node.create_table(
                    self.table_name, 
                    schema
                )
        except Exception as e:
            logger.error(f"Error initializing environment: {str(e)}")
            raise

    async def upsert_simulation(self, run_id: str, messages: List[Dict[str, Any]]):
        """Update existing simulation or insert new one if it doesn't exist."""
        try:
            # Check if the run_id exists
            existing_data = await self.environment_node.query_table(
                self.table_name,
                condition={"run_id": run_id}
            )

            if existing_data["rows"]:
                # Update existing record
                await self.environment_node.update_row(
                    self.table_name,
                    data={"messages": messages},
                    condition={"run_id": run_id}
                )
                logger.info(f"Updated simulation with run_id: {run_id}")
            else:
                # Insert new record
                await self.environment_node.add_row(
                    self.table_name,
                    data={
                        "run_id": run_id,
                        "messages": messages
                    }
                )
                logger.info(f"Inserted new simulation with run_id: {run_id}")

        except Exception as e:
            logger.error(f"Error upserting simulation: {str(e)}")
            raise

    async def get_simulation(self, run_id: str) -> List[Dict[str, Any]]:
        """Retrieve messages for a given run_id."""
        try:
            result = await self.environment_node.query_table(
                self.table_name,
                columns="messages",
                condition={"run_id": run_id}
            )
            return result["rows"][0]["messages"] if result["rows"] else []
        except Exception as e:
            logger.error(f"Error retrieving simulation: {str(e)}")
            raise

    async def call_environment_func(self, environment_run_input: EnvironmentRunInput):
        logger.info(f"Running environment on environment node {self.environment_node.node_url}")
        environment_run = await self.environment_node.run_environment_and_poll(environment_run_input)
        return environment_run