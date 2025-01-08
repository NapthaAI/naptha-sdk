import httpx
import json
from pydantic import BaseModel
from typing import Union, Dict, Any, Optional, List, BinaryIO
from naptha_sdk.schemas import NodeConfigUser
from naptha_sdk.storage.schemas import (
    StorageLocation,
    StorageType,
    StorageObject,
    BaseStorageRequest,
    CreateStorageRequest,
    ReadStorageRequest,
    UpdateStorageRequest,
    DeleteStorageRequest,
    ListStorageRequest,
    SearchStorageRequest
)
from naptha_sdk.utils import get_logger, node_to_url

HTTP_TIMEOUT = 300

logger = get_logger(__name__)

class StorageProvider:
    def __init__(self, node: NodeConfigUser):
        self.node = node
        self.node_url = node_to_url(node)
        self.client = httpx.AsyncClient(timeout=HTTP_TIMEOUT)
        logger.info(f"Storage Provider URL: {self.node_url}")


    async def _make_request(
        self,
        request: BaseStorageRequest,
        files: Optional[Dict] = None
    ) -> Any:
        """Make HTTP request to storage endpoint"""
        endpoint = f"{self.node_url}/storage/{request.storage_type.value}/{request.request_type.value}/{request.path}"
        print(f"Request: {request}")
        try:
            response = None
            match request:
                case CreateStorageRequest():
                    form_data = {}
                    if not request.data:
                        request.data = {}
                    if not request.options:
                        request.options = {}
                    form_data['data'] = json.dumps({**request.data, **request.options})
                    print(f"Form data: {form_data}")
                    files = files if files is not None else {}
                    response = await self.client.post(endpoint, data=form_data, files=files)

                case ReadStorageRequest():
                    if request.storage_type in [StorageType.FILESYSTEM, StorageType.IPFS]:
                        response = await self.client.get(endpoint)
                        response.raise_for_status()
                        # Check content type to determine response handling
                        content_type = response.headers.get('content-type', '')
                        if 'json' in content_type:
                            return response.json()
                        return response.content
                    else:
                        params = {"options": json.dumps(request.options)} if request.options else None
                        response = await self.client.get(endpoint, params=params)
                                        
                case UpdateStorageRequest():
                    # Extract condition from options if present
                    condition = request.options.get("condition") if request.options else None
                    form_data = {
                        'data': json.dumps(request.data)
                    }
                    params = {
                        'condition': json.dumps(condition) if condition else None
                    }
                    response = await self.client.put(endpoint, data=form_data, params=params)
                    
                case ListStorageRequest():
                    params = {"options": json.dumps(request.options)} if request.options else None
                    response = await self.client.get(endpoint, params=params)
                    
                case DeleteStorageRequest():
                    params = {}
                    if request.storage_type == StorageType.DATABASE:
                        if request.condition:
                            params["condition"] = json.dumps(request.condition)
                    elif request.storage_type == StorageType.FILESYSTEM:
                        if request.options:
                            params["options"] = json.dumps(request.options)
                    response = await self.client.delete(endpoint, params=params)
                    
                case SearchStorageRequest():
                    search_data = {
                        "query": request.query,
                        "query_type": request.query_type,
                        "limit": request.limit
                    }
                    response = await self.client.post(endpoint, json=search_data)
            
            if response:
                response.raise_for_status()
                content_type = response.headers.get('content-type', '')
                if 'json' in content_type:
                    return response.json()
                return response.content
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e.response.text}")
            raise StorageError(f"HTTP error occurred: {str(e)}", status_code=e.response.status_code)
        except Exception as e:
            logger.error(f"Storage operation failed: {str(e)}")
            raise StorageError(f"Storage operation failed: {str(e)}")

    async def execute(self, request: BaseStorageRequest) -> Union[StorageObject, List[StorageObject], bool]:
        """Execute storage request and return appropriate response"""
        files = None
        if isinstance(request, CreateStorageRequest) and request.file:
            files = {"file": request.file}
            
        result = await self._make_request(request, files=files)

        match request:
            case DeleteStorageRequest():
                return True
                
            case ListStorageRequest():
                # Handle list response which might be a simple array
                if isinstance(result, list):
                    return [
                        StorageObject(
                            location=StorageLocation(
                                storage_type=request.storage_type,
                                path=request.path
                            ),
                            data=item
                        )
                        for item in result
                    ]
                return StorageObject(
                    location=StorageLocation(storage_type=request.storage_type, path=request.path),
                    data=result
                )
                
            case SearchStorageRequest():
                # Handle search response which returns objects with path
                return [
                    StorageObject(
                        location=StorageLocation(
                            storage_type=request.storage_type,
                            path=obj.get("path", "")
                        ),
                        data=obj.get("data"),
                        metadata=obj.get("metadata")
                    )
                    for obj in result
                ]
                
            case _:
                return StorageObject(
                    location=StorageLocation(
                        storage_type=request.storage_type,
                        path=request.path
                    ),
                    data=result
                )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

class StorageError(Exception):
    """Custom exception for storage operations"""
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)