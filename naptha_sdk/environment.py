from naptha_sdk.client.node import Node
from naptha_sdk.schemas import AgentRun, EnvironmentRunInput, OrchestratorRun
from typing import Any, Dict, List, Union
import logging

logger = logging.getLogger(__name__)

class Environment:
    def __init__(self, module_run: Union[OrchestratorRun, AgentRun]):
        self.module_run = module_run
        self.environment_deployment = module_run.environment_deployments[0]
        self.environment_node = Node(self.environment_deployment.environment_node_url)
        self.table_name = "multi_chat_simulations"

    async def initialize(self):
        """Initialize the environment by creating the table."""
        await self.create_table()
        return self

    @classmethod
    async def create(cls, module_run: Union[OrchestratorRun, AgentRun]):
        """Factory method to create and initialize an Environment instance."""
        instance = cls(module_run)
        await instance.initialize()
        return instance

    async def create_table(self):
        """Create multi_chat_simulations table if it doesn't exist."""
        try:
            schema = {
                "run_id": {"type": "TEXT", "primary_key": True},
                "messages": {"type": "JSONB"}
            }
            await self.environment_node.create_table(self.table_name, schema)
            logger.info("Table created successfully")
        except Exception as e:
            logger.error(f"Error creating table: {str(e)}")
            raise

    def sync_upsert_simulation(self, run_id: str, messages: List[Dict[str, Any]]):
        """Synchronous wrapper for upsert_simulation to be used in non-async contexts."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.upsert_simulation(run_id, messages))

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

    def sync_get_simulation(self, run_id: str) -> List[Dict[str, Any]]:
        """Synchronous wrapper for get_simulation to be used in non-async contexts."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.get_simulation(run_id))

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

    async def call_environment_func(self, *args, **kwargs):
        logger.info(f"Running environment on environment node {self.environment_node.node_url}")

        environment_run_input = EnvironmentRunInput(
            consumer_id=self.module_run.consumer_id,
            inputs=kwargs,
            agent_deployment=self.module_run.agent_deployment.model_dump(),
        )

        environment_run = await self.environment_node.run_environment_and_poll(
            environment_run_input=environment_run_input
        )
        return environment_run