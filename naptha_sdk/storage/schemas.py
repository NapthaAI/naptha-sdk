from enum import Enum
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, Union, List

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

class DatabaseReadOptions(BaseModel):
    """Options specific to database reads"""
    columns: Optional[List[str]] = None
    conditions: Optional[List[Dict[str, Any]]] = None
    order_by: Optional[str] = None
    order_direction: Optional[str] = "asc"
    limit: Optional[int] = None
    offset: Optional[int] = None
    # Added fields for QA/vector search
    query_col: Optional[str] = None  # Column to search against
    answer_col: Optional[str] = None  # Column to return as answer
    vector_col: Optional[str] = None  # Column containing vectors
    top_k: Optional[int] = Field(default=5, ge=1)  # Number of results for vector search
    include_similarity: Optional[bool] = Field(default=True)  # Include similarity scores

class ReadStorageRequest(BaseModel):
    """Unified read request schema"""
    storage_type: StorageType
    path: str
    db_options: Optional[DatabaseReadOptions] = None

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
