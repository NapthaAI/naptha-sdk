import asyncio
import logging
import uuid
import random
import httpx
from typing import List

from naptha_sdk.client.node import Node 
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

NODE_URL = "http://localhost:7001"
HTTP_TIMEOUT = 30

async def drop_table_via_query(node: Node, table_name: str):
    """
    Helper function to drop a table by sending a raw SQL query
    to the /local-db/query endpoint.
    """
    query_str = f"DROP TABLE IF EXISTS {table_name} CASCADE"
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        resp = await client.post(
            f"{node.node_url}/local-db/query",
            json={"query_str": query_str}
        )
        return resp.text  # Could be JSON or text, depending on your server


async def test_regular_table_via_node():
    logger.info("\n=== Testing Regular Table via Node ===")

    node = Node(node_url=NODE_URL)

    # 1) Define schema
    regular_schema = {
        "id": {"type": "text", "primary_key": True},
        "name": {"type": "text"},
        "age": {"type": "integer"},
        "metadata": {"type": "jsonb"},
        "scores": {"type": "float[]"},
        "created_at": {"type": "timestamp", "default": "CURRENT_TIMESTAMP"},
    }
    table_name = "test_regular_http"

    # 2) Drop table if exists
    drop_response = await drop_table_via_query(node, table_name)
    logger.info(f"Drop table response: {drop_response}")

    # 3) Create table
    create_resp = await node.create_table(table_name, regular_schema)
    logger.info(f"Create table response: {create_resp}")

    # 4) Add rows
    test_data = [
        {
            "id": str(uuid.uuid4()),
            "name": "Alice",
            "age": 25,
            "metadata": {"city": "New York", "role": "engineer"},
            "scores": [85.5, 92.0, 88.5],
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Bob",
            "age": 30,
            "metadata": {"city": "San Francisco", "role": "designer"},
            "scores": [90.0, 88.5, 95.0],
        },
    ]
    for row_data in test_data:
        add_resp = await node.add_row(table_name, row_data)
        logger.info(f"Add row response: {add_resp}")

    # 5) Query with filter (age=25)
    filtered = await node.query_table(
        table_name, 
        columns="id,name,age", 
        condition={"age": 25}
    )
    logger.info(f"Filtered query result: {filtered}")

    # 6) Update (age=26 where name='Alice')
    update_resp = await node.update_row(table_name, {"age": 26}, {"name": "Alice"})
    logger.info(f"Update rows response: {update_resp}")

    # 7) Schema retrieval
    schema_resp = await node.get_table_schema(table_name)
    logger.info(f"Table schema: {schema_resp}")

    # 8) List tables
    list_tables_resp = await node.list_tables()
    logger.info(f"List tables response: {list_tables_resp}")

    # 9) Delete row (where name='Bob')
    delete_resp = await node.delete_row(table_name, {"name": "Bob"})
    logger.info(f"Delete rows response: {delete_resp}")

    # 10) Final query (verify changes)
    final_resp = await node.query_table(table_name)
    logger.info(f"Final table state: {final_resp}")


async def test_vector_table_via_node():
    logger.info("\n=== Testing Vector Table via Node ===")

    node = Node(node_url=NODE_URL)

    # 1) Define schema for vectors
    vector_schema = {
        "id": {"type": "text", "primary_key": True},
        "text": {"type": "text"},
        "embedding": {"type": "vector", "dimension": 4},
        "metadata": {"type": "jsonb"},
    }
    table_name = "test_vectors_http"

    # 2) Drop table if exists
    await drop_table_via_query(node, table_name)

    # 3) Create table
    create_resp = await node.create_table(table_name, vector_schema)
    logger.info(f"Create vector table response: {create_resp}")

    # 4) Insert sample docs
    def generate_random_vector(dim: int = 4) -> List[float]:
        # return list(np.random.randn(dim).astype(float))
        # use random library
        return list(random.random() for _ in range(dim))

    test_docs = [
        ("First document", "test"),
        ("Second document", "test"),
        ("Third document", "other"),
    ]
    for text_doc, category in test_docs:
        row_data = {
            "id": str(uuid.uuid4()),
            "text": text_doc,
            "embedding": generate_random_vector(),
            "metadata": {"category": category},
        }
        await node.add_row(table_name, row_data)

    # 5) Basic retrieval
    all_docs = await node.query_table(table_name)
    logger.info(f"All vector table docs: {all_docs}")

    # 6) Vector similarity search (basic)
    query_vec = generate_random_vector()
    sim_search_basic = await node.vector_search(
        table_name=table_name,
        vector_column="embedding",
        query_vector=query_vec,
        columns=["text"],
        top_k=2,
        include_similarity=True
    )
    logger.info(f"Similarity search (basic): {sim_search_basic}")

    # 7) Vector similarity search (full)
    sim_search_full = await node.vector_search(
        table_name=table_name,
        vector_column="embedding",
        query_vector=query_vec,
        columns=["id", "text", "metadata"],
        top_k=2,
        include_similarity=True
    )
    logger.info(f"Similarity search (full): {sim_search_full}")

    # 8) Update a row
    rows = all_docs.get("rows", [])
    if rows:
        test_id = rows[0]["id"]
        update_data = {
            "embedding": generate_random_vector(),
            "metadata": {"category": "updated"},
        }
        await node.update_row(table_name, update_data, {"id": test_id})

        # 9) Verify update
        updated = await node.query_table(table_name, condition={"id": test_id})
        logger.info(f"Updated row: {updated}")

    # 10) Inspect schema
    schema_resp = await node.get_table_schema(table_name)
    logger.info(f"Vector table schema: {schema_resp}")


async def main():
    try:
        await test_regular_table_via_node()
        await test_vector_table_via_node()
        logger.info("\nAll tests completed successfully via Node client!")
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
