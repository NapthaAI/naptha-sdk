from naptha_sdk.schemas import NodeSchema
from naptha_sdk.storage.schemas import StorageType
from naptha_sdk.utils import get_logger, node_to_url
import httpx
import json
from typing import Optional, Union, Dict, Any, List
from httpx import HTTPStatusError, RemoteProtocolError
from naptha_sdk.storage.schemas import ReadStorageRequest, CreateTableRequest, CreateRowRequest, DeleteTableRequest, DeleteRowRequest, ListRowsRequest

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
        create_storage_request: Union[CreateTableRequest, CreateRowRequest]
    ) -> Dict[str, Any]:
        """
        Create new storage objects (table, file, or IPFS content)
        
        Args:
            create_storage_request: CreateStorageRequest
        """
        endpoint = f"{self.node_url}/storage/{create_storage_request.storage_type.value}/create/{create_storage_request.path}"

        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                # Convert request to dict and remove None values
                request_data = create_storage_request.model_dump(exclude_none=True)
                # Remove storage_type and path from request data
                request_data.pop('storage_type', None)
                request_data.pop('path', None)
                
                response = await client.post(
                    endpoint,
                    json=request_data
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

    async def delete(
        self,
        delete_storage_request: Union[DeleteTableRequest, DeleteRowRequest]
    ) -> Dict[str, Any]:
        """
        Delete storage objects (table, file, or IPFS content)
        
        Args:
            delete_storage_request: DeleteStorageRequest
        """
        endpoint = f"{self.node_url}/storage/{delete_storage_request.storage_type.value}/delete/{delete_storage_request.path}"

        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                params = {}
                if hasattr(delete_storage_request, 'condition'):
                    params['condition'] = json.dumps(delete_storage_request.condition)

                response = await client.delete(
                    endpoint,
                    params=params
                )
                response.raise_for_status()
                return response.json()

        except HTTPStatusError as e:
            logger.info(f"HTTP error occurred: {e}")
            raise
        except RemoteProtocolError as e:
            error_msg = f"Storage deletion failed to connect to the server at {self.node_url}. Please check if the server URL is correct and the server is running. Error details: {str(e)}"
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
        list_storage_request: ListRowsRequest
    ) -> Dict[str, Any]:
        """
        List storage objects (DB tables/rows, directory contents, IPFS directory)
        
        Args:
            list_storage_request: ListStorageRequest
        """
        endpoint = f"{self.node_url}/storage/{list_storage_request.storage_type.value}/list/{list_storage_request.path}"

        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                response = await client.get(endpoint, params={"limit": list_storage_request.limit if list_storage_request.limit else None})
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