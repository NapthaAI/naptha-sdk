import json
import psycopg2
import logging
from naptha_sdk.client.node import Node
from naptha_sdk.schemas import AgentRun, EnvironmentRunInput, OrchestratorRun
from typing import Any, Dict, List, Union


logger = logging.getLogger(__name__)


class Environment:
    def __init__(self, module_run: Union[OrchestratorRun, AgentRun]):
        self.module_run = module_run
        self.environment_deployment = module_run.environment_deployment
        self.db_url = self.environment_deployment.environment_node_url
        self.environment_node = Node(self.environment_deployment.environment_node_url)
        self.conn = psycopg2.connect(self.db_url)
        self.cursor = self.conn.cursor()
        self.create_table()

    def __del__(self):
        if hasattr(self, 'cursor') and self.cursor:
            self.cursor.close()
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()

    def create_table(self):
        """Create multi_chat_simulations table if it doesn't exist."""
        try:
            query = """
            CREATE TABLE IF NOT EXISTS multi_chat_simulations (
                run_id TEXT PRIMARY KEY,
                messages JSONB
            )
            """
            self.cursor.execute(query)
            self.conn.commit()
            logger.info("Table created successfully")
        
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error creating table: {str(e)}")
            raise

    def upsert_simulation(self, run_id: str, messages: List[Dict[str, Any]]):
        """Update existing simulation or insert new one if it doesn't exist."""
        try:
            # First check if the run_id exists
            check_query = """
            SELECT EXISTS(SELECT 1 FROM multi_chat_simulations WHERE run_id = %s)
            """
            self.cursor.execute(check_query, (run_id,))
            exists = self.cursor.fetchone()[0]

            if exists:
                # Update existing record
                update_query = """
                UPDATE multi_chat_simulations 
                SET messages = messages || %s::jsonb
                WHERE run_id = %s
                """
                self.cursor.execute(update_query, (
                    json.dumps(messages),
                    run_id
                ))
                logger.info(f"Updated simulation with run_id: {run_id}")
            else:
                # Insert new record
                insert_query = """
                INSERT INTO multi_chat_simulations (run_id, messages)
                VALUES (%s, %s)
                """
                self.cursor.execute(insert_query, (
                    run_id,
                    json.dumps(messages)
                ))
                logger.info(f"Inserted new simulation with run_id: {run_id}")

            self.conn.commit()
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error upserting simulation: {str(e)}")
            raise

    def get_simulation(self, run_id: str) -> List[Dict[str, Any]]:
        """Retrieve messages for a given run_id."""
        try:
            query = """
            SELECT messages FROM multi_chat_simulations WHERE run_id = %s
            """
            self.cursor.execute(query, (run_id,))
            result = self.cursor.fetchone()
            return result[0] if result else []
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

        environment_run = await self.environment_node.run_environment_and_poll(environment_run_input=environment_run_input)
        return environment_run

