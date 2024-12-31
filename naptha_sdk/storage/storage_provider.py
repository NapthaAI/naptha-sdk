from naptha_sdk.schemas import NodeSchema
from naptha_sdk.storage.schemas import StorageType
from naptha_sdk.utils import get_logger, node_to_url
import httpx
import json
from typing import Optional, Union, Dict, Any, List
from httpx import HTTPStatusError, RemoteProtocolError
from naptha_sdk.storage.schemas import ReadStorageRequest

HTTP_TIMEOUT = 300

logger = get_logger(__name__)

class StorageProvider:
    def __init__(self, node: NodeSchema):
        self.node = node
        self.node_url = node_to_url(node)
        self.connections = {}
        
        logger.info(f"Storage Provider URL: {self.node_url}")

    async def create(
        self,
        storage_type: StorageType,
        path: str,
        file: Optional[Union[bytes, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        schema: Optional[Dict[str, Any]] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create new storage objects (table, file, or IPFS content)
        
        Args:
            storage_type: Type of storage ('database', 'filesystem', or 'ipfs')
            path: Storage path/identifier
            file: File content for fs/ipfs storage types
            data: JSON data for database storage
            schema: Schema for database tables
            options: Storage-specific options
        """
        endpoint = f"{self.node_url}/storage/{storage_type}/create"

        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                # Prepare form data
                files = {'file': file} if file else None
                data = {
                    'path': path,
                    'data': json.dumps(data) if data else None,
                    'schema': json.dumps(schema) if schema else None,
                    'options': json.dumps(options) if options else None
                }
                
                # Remove None values
                data = {k: v for k, v in data.items() if v is not None}

                response = await client.post(
                    endpoint,
                    data=data,
                    files=files
                )
                response.raise_for_status()
                return response.json()

        except HTTPStatusError as e:
            logger.info(f"HTTP error occurred: {e}")
            raise
        except RemoteProtocolError as e:
            error_msg = f"Storage creation failed to connect to the server at {self.node_url}. Please check if the server URL is correct and the server is running. Error details: {str(e)}"
            logger.error(error_msg)
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            raise

    async def read(
        self,
        read_storage_request: ReadStorageRequest,
    ) -> Dict[str, Any]:
        """
        Read from storage (query DB, read file, or fetch IPFS content)
        
        Args:
            read_storage_request: ReadStorageRequest
        """
        endpoint = f"{self.node_url}/storage/{read_storage_request.storage_type.value}/read/{read_storage_request.path}"

        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                params = read_storage_request.db_options.model_dump(exclude_none=True)

                print("TTTTT", params)

                response = await client.get(endpoint, params=params)
                response.raise_for_status()
                return response.json()

        except HTTPStatusError as e:
            logger.info(f"HTTP error occurred: {e}")
            raise
        except RemoteProtocolError as e:
            error_msg = f"Storage read failed to connect to the server at {self.node_url}. Please check if the server URL is correct and the server is running. Error details: {str(e)}"
            logger.error(error_msg)
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            raise

    async def list(
        self,
        storage_type: StorageType,
        path: str,
        pattern: Optional[str] = None,
        recursive: bool = False,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        List storage objects (DB tables/rows, directory contents, IPFS directory)
        
        Args:
            storage_type: Type of storage ('database', 'filesystem', or 'ipfs')
            path: Storage path/identifier
            pattern: Filter pattern
            recursive: List recursively
            limit: Result limit
        """
        endpoint = f"{self.node_url}/storage/{storage_type}/list/{path}"

        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                params = {
                    'pattern': pattern,
                    'recursive': recursive,
                    'limit': limit
                }
                # Remove None values
                params = {k: v for k, v in params.items() if v is not None}

                response = await client.get(endpoint, params=params)
                response.raise_for_status()
                return response.json()

        except HTTPStatusError as e:
            logger.info(f"HTTP error occurred: {e}")
            raise
        except RemoteProtocolError as e:
            error_msg = f"Storage listing failed to connect to the server at {self.node_url}. Please check if the server URL is correct and the server is running. Error details: {str(e)}"
            logger.error(error_msg)
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            raise

    async def search(
        self,
        storage_type: StorageType,
        path: str,
        query: Union[str, Dict[str, Any], List[float]],
        query_type: str = "text",
        limit: Optional[int] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Search across storage (DB query, file content search, IPFS search)
        
        Args:
            storage_type: Type of storage ('database', 'filesystem', or 'ipfs')
            path: Storage path/identifier
            query: Search query (text string, metadata dict, or vector)
            query_type: Query type (text, vector, metadata)
            limit: Result limit
            options: Storage-specific options
        """
        endpoint = f"{self.node_url}/storage/{storage_type}/search"

        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                data = {
                    'path': path,
                    'query': query,
                    'query_type': query_type,
                    'limit': limit,
                    'options': options
                }
                # Remove None values
                data = {k: v for k, v in data.items() if v is not None}

                response = await client.post(endpoint, json=data)
                response.raise_for_status()
                return response.json()

        except HTTPStatusError as e:
            logger.info(f"HTTP error occurred: {e}")
            raise
        except RemoteProtocolError as e:
            error_msg = f"Storage search failed to connect to the server at {self.node_url}. Please check if the server URL is correct and the server is running. Error details: {str(e)}"
            logger.error(error_msg)
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            raise