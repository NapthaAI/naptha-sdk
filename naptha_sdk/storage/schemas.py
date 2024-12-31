from enum import Enum
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, Union

class StorageType(str, Enum):
    DATABASE = "db"
    FILESYSTEM = "fs"
    IPFS = "ipfs"

class CreateTableRequest(BaseModel):
    storage_type: StorageType
    path: str
    schema: Dict[str, Any]

class CreateRowRequest(BaseModel):
    storage_type: StorageType
    path: str
    data: Dict[str, Any]

class BaseStorageRequest(BaseModel):
    storage_type: StorageType
    path: str
    options: Dict[str, Any] = Field(default_factory=dict)

class CreateTableRequest(BaseStorageRequest):
    schema: Dict[str, Any]

class CreateRowRequest(BaseStorageRequest):
    data: Dict[str, Any]

class ReadStorageRequest(BaseModel):
    """Unified read request schema"""
    path: str
    storage_type: StorageType
    condition: Optional[Dict[str, Any]] = None

class UpdateStorageRequest(BaseModel):
    data: Union[Dict[str, Any], bytes]
    condition: Optional[Dict[str, Any]] = None
    options: Dict[str, Any] = Field(default_factory=dict)

class SearchStorageRequest(BaseModel):
    path: str
    query: Union[str, Dict[str, Any], list[float]]
    query_type: str = "text"
    limit: Optional[int] = None
    options: Dict[str, Any] = Field(default_factory=dict)
