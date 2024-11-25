import psycopg2
import logging
import json
from typing import List, Dict, Any, Optional, Union
from psycopg2.extras import RealDictCursor
from datetime import datetime

logger = logging.getLogger(__name__)

class SchemaValidator:
    """Validator for database schemas"""
    
    VALID_TYPES = {
        'text': str,
        'integer': int,
        'float': float,
        'boolean': bool,
        'jsonb': (dict, list),
        'timestamp': datetime,
        'text[]': list,
        'integer[]': list,
        'float[]': list
    }
    
    @staticmethod
    def validate_schema(data: Dict[str, Any], schema: Dict[str, Dict[str, Any]], partial: bool = False) -> bool:
        """
        Validate data against schema
        Args:
            data: Data to validate
            schema: Schema definition
            partial: If True, only validate fields that are present in data
        Returns:
            bool: True if valid, raises ValueError if invalid
        """
        for field, properties in schema.items():
            # For partial validation, only check fields that are present in data
            if partial and field not in data:
                continue
                
            # Check required fields (only if not partial)
            if not partial and properties.get('required', False) and field not in data:
                raise ValueError(f"Required field '{field}' is missing")
            
            # Skip validation if field is not present and not required
            if field not in data:
                continue
                
            field_type = properties['type']
            field_value = data[field]
            
            # Handle NULL values
            if field_value is None:
                if properties.get('required', False):
                    raise ValueError(f"Required field '{field}' cannot be NULL")
                continue
            
            # Validate type
            expected_type = SchemaValidator.VALID_TYPES.get(field_type)
            if not expected_type:
                raise ValueError(f"Unknown type '{field_type}' in schema")
                
            if not isinstance(field_value, expected_type):
                raise ValueError(f"Field '{field}' should be of type {expected_type}, got {type(field_value)}")
            
            # Validate array types if specified
            if field_type.endswith('[]'):
                array_type = SchemaValidator.VALID_TYPES[field_type[:-2]]
                if not all(isinstance(item, array_type) for item in field_value):
                    raise ValueError(f"Array field '{field}' should contain only {array_type} values")
                    
        return True

class LocalDBClient:
    def __init__(self, db_url: str):
        """
        Initialize LocalDB (postgres or sqlite) client
        Args:
            db_url: Database connection URL
        """
        self.db_url = db_url
        self.conn = psycopg2.connect(db_url)
        self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)

    def __del__(self):
        """Clean up database connections"""
        if hasattr(self, 'cursor') and self.cursor:
            self.cursor.close()
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()

    def create_table(self, table_name: str, schema: Dict[str, Dict[str, Any]]) -> bool:
        """
        Create a table if it doesn't exist
        Args:
            table_name: Name of the table
            schema: Schema definition
        Returns:
            bool: True if successful
        """
        try:
            # Convert schema to PostgreSQL types
            columns = []
            for field, properties in schema.items():
                column_def = f"{field} {properties['type'].upper()}"
                if properties.get('primary_key', False):
                    column_def += " PRIMARY KEY"
                if properties.get('required', False):
                    column_def += " NOT NULL"
                if 'default' in properties:
                    column_def += f" DEFAULT {properties['default']}"
                columns.append(column_def)

            query = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                {', '.join(columns)}
            )
            """
            self.cursor.execute(query)
            self.conn.commit()
            logger.info(f"Table {table_name} created or already exists")
            return True
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error creating table: {str(e)}")
            raise

    def add_row(self, table_name: str, data: Dict[str, Any], schema: Dict[str, Dict[str, Any]]) -> bool:
        """
        Add a row to the table
        Args:
            table_name: Name of the table
            data: Data to insert
            schema: Schema definition
        Returns:
            bool: True if successful
        """
        try:
            # Validate data against schema
            SchemaValidator.validate_schema(data, schema)
            
            columns = list(data.keys())
            values = []
            
            # Process values based on their types
            for col in columns:
                value = data[col]
                field_type = schema[col]['type']
                
                if field_type == 'jsonb':
                    values.append(json.dumps(value))
                elif field_type.endswith('[]'):
                    # Convert list to PostgreSQL array format
                    if not value:
                        values.append('{}')
                    else:
                        array_str = '{' + ','.join(str(x) for x in value) + '}'
                        values.append(array_str)
                else:
                    values.append(value)
            
            placeholders = ["%s"] * len(columns)
            
            query = f"""
            INSERT INTO {table_name} ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
            """
            self.cursor.execute(query, values)
            self.conn.commit()
            logger.info(f"Row added to table {table_name}")
            return True
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error adding row: {str(e)}")
            raise

    def delete_row(self, table_name: str, condition: Dict[str, Any]) -> int:
        """
        Delete rows from the table
        Args:
            table_name: Name of the table
            condition: Conditions for deletion
        Returns:
            int: Number of rows deleted
        """
        try:
            where_clause = " AND ".join([f"{k} = %s" for k in condition.keys()])
            values = list(condition.values())
            
            query = f"""
            DELETE FROM {table_name}
            WHERE {where_clause}
            """
            self.cursor.execute(query, values)
            rows_deleted = self.cursor.rowcount
            self.conn.commit()
            logger.info(f"Deleted {rows_deleted} rows from {table_name}")
            return rows_deleted
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error deleting row: {str(e)}")
            raise

    def update_row(self, table_name: str, data: Dict[str, Any], 
                condition: Dict[str, Any], schema: Dict[str, Dict[str, Any]]) -> int:
        """
        Update rows in the table
        Args:
            table_name: Name of the table
            data: Data to update
            condition: Conditions for update
            schema: Schema definition
        Returns:
            int: Number of rows updated
        """
        try:
            # Validate update data against schema with partial validation
            SchemaValidator.validate_schema(data, schema, partial=True)
            
            # Process update values
            update_values = []
            for col in data.keys():
                value = data[col]
                field_type = schema[col]['type']
                
                if field_type == 'jsonb':
                    update_values.append(json.dumps(value))
                elif field_type.endswith('[]'):
                    if not value:
                        update_values.append('{}')
                    else:
                        array_str = '{' + ','.join(str(x) for x in value) + '}'
                        update_values.append(array_str)
                else:
                    update_values.append(value)
            
            # Process condition values
            condition_values = list(condition.values())
            
            set_clause = ", ".join([f"{k} = %s" for k in data.keys()])
            where_clause = " AND ".join([f"{k} = %s" for k in condition.keys()])
            values = update_values + condition_values
            
            query = f"""
            UPDATE {table_name}
            SET {set_clause}
            WHERE {where_clause}
            """
            self.cursor.execute(query, values)
            rows_updated = self.cursor.rowcount
            self.conn.commit()
            logger.info(f"Updated {rows_updated} rows in {table_name}")
            return rows_updated
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error updating row: {str(e)}")
            raise

    def query(self, table_name: str, columns: Optional[List[str]] = None, 
              condition: Optional[Dict[str, Any]] = None,
              order_by: Optional[str] = None,
              limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Query the table
        Args:
            table_name: Name of the table
            columns: Columns to select
            condition: Query conditions
            order_by: Order by clause
            limit: Limit results
        Returns:
            List[Dict[str, Any]]: Query results
        """
        try:
            select_clause = "*" if not columns else ", ".join(columns)
            query = f"SELECT {select_clause} FROM {table_name}"
            values = []
            
            if condition:
                where_clause = " AND ".join([f"{k} = %s" for k in condition.keys()])
                values = list(condition.values())
                query += f" WHERE {where_clause}"
            
            if order_by:
                query += f" ORDER BY {order_by}"
                
            if limit:
                query += f" LIMIT {limit}"
            
            self.cursor.execute(query, values)
            results = self.cursor.fetchall()
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Error querying table: {str(e)}")
            raise


if __name__ == "__main__":
    import logging
    import os
    import uuid
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    def run_test(test_func):
        try:
            test_func()
            logger.info(f"✅ {test_func.__name__} passed")
        except Exception as e:
            logger.error(f"❌ {test_func.__name__} failed: {str(e)}")
            raise

    def test_schema_validator():
        """Test schema validation"""
        schema = {
            "id": {
                "type": "text",
                "primary_key": True,
                "required": True
            },
            "count": {
                "type": "integer",
                "required": False
            },
            "tags": {
                "type": "text[]",
                "required": False
            }
        }

        # Valid data
        valid_data = {
            "id": str(uuid.uuid4()),
            "count": 42,
            "tags": ["tag1", "tag2"]
        }
        SchemaValidator.validate_schema(valid_data, schema)
        logger.info("Valid schema validation passed")

        # Test invalid data
        try:
            invalid_data = {
                "id": 123,  # should be string
                "count": "invalid",  # should be integer
            }
            SchemaValidator.validate_schema(invalid_data, schema)
            raise AssertionError("Should have failed validation")
        except ValueError:
            logger.info("Invalid schema validation caught as expected")

    def test_table_operations():
        """Test table creation and basic operations"""
        # Get PostgreSQL connection details from environment variables
        db_params = {
            "dbname": os.getenv("LOCAL_DB_NAME", "naptha"),
            "user": os.getenv("LOCAL_DB_USER", "naptha"),
            "password": os.getenv("LOCAL_DB_PASSWORD", "napthapassword"),
            "host": os.getenv("LOCAL_DB_HOST", "localhost"),
            "port": os.getenv("LOCAL_DB_PORT", "3002")
        }
        
        # Create PostgreSQL connection string
        db_url = f"postgresql://{db_params['user']}:{db_params['password']}@{db_params['host']}:{db_params['port']}/{db_params['dbname']}"
        
        client = LocalDBClient(db_url)

        # Define test schema
        schema = {
            "id": {
                "type": "text",
                "primary_key": True,
                "required": True
            },
            "name": {
                "type": "text",
                "required": True
            },
            "age": {
                "type": "integer",
                "required": False
            },
            "metadata": {
                "type": "jsonb",
                "required": False
            }
        }

        # Create table
        client.create_table("test_users", schema)
        logger.info("Table created successfully")

        # Generate unique ID
        test_id = str(uuid.uuid4())
        logger.info(f"Generated test ID: {test_id}")

        # Test data insertion
        test_data = {
            "id": test_id,
            "name": "John Doe",
            "age": 30,
            "metadata": {"interests": ["coding", "reading"]}
        }
        client.add_row("test_users", test_data, schema)
        logger.info("Row added successfully")

        # Test query
        results = client.query("test_users", condition={"id": test_id})
        assert len(results) == 1
        assert results[0]["name"] == "John Doe"
        logger.info("Query successful")

        # Test update
        update_data = {"age": 31}
        client.update_row("test_users", update_data, {"id": test_id}, schema)
        updated_results = client.query("test_users", condition={"id": test_id})
        assert updated_results[0]["age"] == 31
        logger.info("Update successful")

        # Test delete
        deleted_count = client.delete_row("test_users", {"id": test_id})
        assert deleted_count == 1
        logger.info("Delete successful")

        client.__del__()

    def test_complex_queries():
        """Test more complex query operations"""
        # Get PostgreSQL connection details from environment variables
        db_params = {
            "dbname": os.getenv("LOCAL_DB_NAME", "naptha"),
            "user": os.getenv("LOCAL_DB_USER", "naptha"),
            "password": os.getenv("LOCAL_DB_PASSWORD", "napthapassword"),
            "host": os.getenv("LOCAL_DB_HOST", "localhost"),
            "port": os.getenv("LOCAL_DB_PORT", "3002")
        }
        
        db_url = f"postgresql://{db_params['user']}:{db_params['password']}@{db_params['host']}:{db_params['port']}/{db_params['dbname']}"
        client = LocalDBClient(db_url)

        schema = {
            "id": {
                "type": "text",
                "primary_key": True,
                "required": True
            },
            "name": {
                "type": "text",
                "required": True
            },
            "score": {
                "type": "integer",
                "required": True
            }
        }

        # Create table and insert test data
        client.create_table("test_scores", schema)
        test_data = [
            {"id": str(uuid.uuid4()), "name": f"User {i}", "score": i * 10}
            for i in range(1, 6)
        ]
        for data in test_data:
            client.add_row("test_scores", data, schema)
            logger.info(f"Added test score data: {data['name']} with ID: {data['id']}")

        # Test ordered query
        ordered_results = client.query(
            "test_scores",
            columns=["name", "score"],
            order_by="score DESC",
            limit=3
        )
        assert len(ordered_results) == 3
        assert ordered_results[0]["score"] > ordered_results[1]["score"]
        logger.info("Complex query successful")

        # Clean up test data
        for data in test_data:
            client.delete_row("test_scores", {"id": data["id"]})
        logger.info("Test data cleaned up")

        client.__del__()

    logger.info("Starting LocalDB Client tests...")
    
    run_test(test_schema_validator)
    run_test(test_table_operations)
    run_test(test_complex_queries)
    
    logger.info("All tests completed!")