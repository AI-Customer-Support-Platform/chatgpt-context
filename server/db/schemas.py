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
    created_at: datetime.datetime
    updated_at: datetime.datetime
    documents: List[DocumentFile] = []

    class Config:
        orm_mode = True

class UserBase(BaseModel):
    owner: str
    email: str
    stripe_id: str | None = None

class PlanBase(BaseModel):
    platform: str
    plan: str
    suscription_id: str

class PlanCreate(PlanBase):
    pass

class Plan(PlanBase):
    id: int

class User(UserBase):
    plans: List[Plan] = []

    class Config:
        orm_mode = True

class PlanConfig(BaseModel):
    price_id: str
    platform: str
    plan: str
    
    file_limit: int
    token_limit: int