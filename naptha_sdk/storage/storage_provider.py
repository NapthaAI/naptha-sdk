import httpx
from httpx import HTTPStatusError, RemoteProtocolError
import json
from typing import Union, Dict, Any
from naptha_sdk.schemas import NodeSchema
from naptha_sdk.storage.schemas import ReadStorageRequest, CreateTableRequest, CreateRowRequest, DeleteStorageRequest, ListStorageRequest, UpdateStorageRequest, SearchStorageRequest
from naptha_sdk.utils import get_logger, node_to_url

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
                request_data = create_storage_request.model_dump(exclude_none=True)
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
                params = read_storage_request.options.model_dump(exclude_none=True)
                response = await client.get(endpoint, params={"options": json.dumps(params)})
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

    async def update(
        self,
        update_storage_request: UpdateStorageRequest
    ) -> Dict[str, Any]:
        """
        Update storage objects (DB rows, file contents, or IPFS content)
        
        Args:
            update_storage_request: UpdateStorageRequest
        """
        endpoint = f"{self.node_url}/storage/{update_storage_request.storage_type.value}/update/{update_storage_request.path}"

        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                request_data = update_storage_request.model_dict()
                
                response = await client.put(
                    endpoint,
                    json=request_data
                )
                response.raise_for_status()
                return response.json()

        except HTTPStatusError as e:
            logger.info(f"HTTP error occurred: {e}")
            raise
        except RemoteProtocolError as e:
            error_msg = f"Storage update failed to connect to the server at {self.node_url}. Please check if the server URL is correct and the server is running. Error details: {str(e)}"
            logger.error(error_msg)
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            raise

    async def delete(
        self,
        delete_storage_request: DeleteStorageRequest
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

    async def list(
        self,
        list_storage_request: ListStorageRequest
    ) -> Dict[str, Any]:
        """
        List storage objects (DB tables/rows, directory contents, IPFS directory)
        
        Args:
            list_storage_request: ListStorageRequest
        """
        endpoint = f"{self.node_url}/storage/{list_storage_request.storage_type.value}/list/{list_storage_request.path}"

        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                params = list_storage_request.options.model_dump(exclude_none=True)
                response = await client.get(endpoint, params={"options": json.dumps(params)})
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
        search_storage_request: SearchStorageRequest
    ) -> Dict[str, Any]:
        """
        Search across storage (DB query, file content search, IPFS search)
        
        Args:
            search_storage_request: SearchStorageRequest
        """
        endpoint = f"{self.node_url}/storage/{search_storage_request.storage_type.value}/search/{search_storage_request.path}"

        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                request_data = search_storage_request.model_dump(exclude_none=True)
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
            error_msg = f"Storage search failed to connect to the server at {self.node_url}. Please check if the server URL is correct and the server is running. Error details: {str(e)}"
            logger.error(error_msg)
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            raise
