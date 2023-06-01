from models.models import (
    Document,
    DocumentMetadataFilter,
    Query,
    QueryResult
)
from models.chat_history import QAHistory
from pydantic import BaseModel
from typing import List, Optional


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