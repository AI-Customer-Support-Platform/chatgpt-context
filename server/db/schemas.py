from pydantic import BaseModel
from typing import List
from uuid import UUID
import datetime

class DocumentFileCreate(BaseModel):
    file_name: str
    collection_id: UUID

class DocumentFile(DocumentFileCreate):
    id: UUID
    create_at: datetime.datetime

class CollectionBase(BaseModel):
    owner: str
    name: str
    description: str | None = None

class CollectionCreate(CollectionBase):
    pass

class Collection(CollectionBase):
    id: UUID
    create_at: datetime.datetime
    documents: List[DocumentFile] = []

    class Config:
        orm_mode = True
