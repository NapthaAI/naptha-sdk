from enum import Enum
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, Union, List

class StorageType(str, Enum):
    DATABASE = "db"
    FILESYSTEM = "fs"
    IPFS = "ipfs"

class DatabaseReadOptions(BaseModel):
    """Options specific to database reads"""
    columns: Optional[List[str]] = None
    conditions: Optional[List[Dict[str, Any]]] = None
    order_by: Optional[str] = None
    order_direction: Optional[str] = "asc"
    limit: Optional[int] = None
    offset: Optional[int] = None
    # fields for QA/vector search
    query_vector: Optional[List[float]] = None
    query_col: Optional[str] = None  # Column to search against
    answer_col: Optional[str] = None  # Column to return as answer
    vector_col: Optional[str] = None  # Column containing vectors
    top_k: Optional[int] = Field(default=5, ge=1)  # Number of results for vector search
    include_similarity: Optional[bool] = Field(default=True)  # Include similarity scores

class BaseStorageRequest(BaseModel):
    storage_type: StorageType
    path: str
    options: Union[Dict[str, Any], DatabaseReadOptions] = Field(default_factory=dict)

    def model_dict(self):
        model_dict = self.dict()
        if isinstance(self.options, BaseModel):
            options = self.options.model_dump()
            model_dict['options'] = options
        model_dict['storage_type'] = self.storage_type.value
        return model_dict

class CreateTableRequest(BaseStorageRequest):
    schema: Dict[str, Any]

class CreateRowRequest(BaseStorageRequest):
    data: Dict[str, Any]

class ReadStorageRequest(BaseStorageRequest):
    pass

class UpdateStorageRequest(BaseStorageRequest):
    pass

class DeleteStorageRequest(BaseStorageRequest):
    pass

class ListStorageRequest(BaseStorageRequest):
    pass

class SearchStorageRequest(BaseStorageRequest):
    pass

