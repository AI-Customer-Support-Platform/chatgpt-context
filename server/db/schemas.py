from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID
import datetime

class DocumentFileCreate(BaseModel):
    file_name: str
    file_size: int
    collection_id: UUID

class DocumentFile(DocumentFileCreate):
    id: UUID
    create_at: datetime.datetime

class CollectionBase(BaseModel):
    owner: str
    name: str
    description: str | None = None
    line_channel_access_token: Optional[str] = ""
    line_language: Optional[str] = "ja"
    fallback_msg: Optional[str] = "Token Limit Reached"

class CollectionCreate(CollectionBase):
    pass

class Collection(CollectionBase):
    id: UUID
    created_at: datetime.datetime
    updated_at: datetime.datetime
    fallback_msg: str
    line_channel_access_token: Optional[str] = ""
    line_language: Optional[str] = "ja"
    
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