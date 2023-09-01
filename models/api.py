from models.models import (
    Document,
    DocumentMetadataFilter,
    Query,
    QueryResult
)
from models.chat import QAHistory
from models.payments import SubscriptionPlatform, SubscriptionType, allSubscriptionInfo
from pydantic import BaseModel
from typing import List, Optional, Any
from server.db.schemas import Collection
from uuid import UUID
import datetime

class UpsertRequest(BaseModel):
    documents: List[Document]


class UpsertResponse(BaseModel):
    ids: List[str]


class QueryRequest(BaseModel):
    queries: List[Query]


class QueryResponse(BaseModel):
    results: List[QueryResult]


class DeleteRequest(BaseModel):
    ids: Optional[List[str]] = None
    filter: Optional[DocumentMetadataFilter] = None
    delete_all: Optional[bool] = False


class DeleteResponse(BaseModel):
    success: bool


class CreateCollectionRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    fallback_msg: Optional[str] = "Token Limit Reached"
    line_channel_access_token: Optional[str] = ""
    line_language: Optional[str] = "ja"


class CreateCollectionResponse(BaseModel):
    id: UUID
    owner: str
    name: str
    description: str

class UserCollectionResponse(BaseModel):
    owner: str
    collections: Any

class UpdateCollectionResponse(CreateCollectionResponse):
    fallback_msg: str
    line_channel_access_token: Optional[str] = ""
    line_language: Optional[str] = "ja"
    created_at: datetime.datetime
    updated_at: datetime.datetime 

class CollectionFileResponse(UpdateCollectionResponse):
    documents: Any

class ChatRequest(BaseModel):
    question: str
    collection: Optional[str] = None
    model: Optional[str] = "gpt-3.5-turbo"

class ChatResponse(BaseModel):
    response: str
    model: Optional[str] = "gpt-3.5-turbo"

class ChatHistoryResponse(BaseModel):
    user_id: str
    exist: bool = False
    history: List[QAHistory]

class CreateStripeSubscriptionRequest(BaseModel):
    api: SubscriptionPlatform
    plan: SubscriptionType
    url: str

class RedirectUrlResponse(BaseModel):
    url: str

class SubscriptionInfoReturn(allSubscriptionInfo):
    pass

class SubscriptionStorageReturn(BaseModel):
    remaining_space: int
    total_space: int