from pydantic import BaseModel
from uuid import UUID

class CollectionBase(BaseModel):
    owner: str
    name: str
    description: str | None = None

class CollectionCreate(CollectionBase):
    pass

class Collection(CollectionBase):
    id: UUID
