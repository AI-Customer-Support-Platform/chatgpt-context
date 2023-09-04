
from uuid import UUID

from fastapi import (
    FastAPI, 
    File, 
    Form, 
    Depends,
    HTTPException, 
    Body, 
    UploadFile,
    Response,
    APIRouter
)
from typing import Optional, Annotated
from loguru import logger

from models.models import DocumentMetadata, Source
from models.api import (
    DeleteRequest,
    DeleteResponse,
    QueryRequest,
    QueryResponse,
    UpsertRequest,
    UpsertResponse,
    CreateCollectionRequest,
    CreateCollectionResponse,
    UpdateCollectionResponse,
    CollectionFileResponse,
    UserCollectionResponse
)
from services.file import get_document_from_file
from datastore.providers.qdrant_datastore import QdrantDataStore
from datastore.providers.redis_chat import RedisChat

from server.db import crud, models, schemas
from .deps import get_db, validate_user_info, validate_token
from sqlalchemy.orm import Session

router = APIRouter()
datastore = QdrantDataStore()
cache = RedisChat()

def validate_user(
    collection: UUID,
    user: str = Depends(validate_token),
    db: Session = Depends(get_db),
):
    if not crud.check_collection_owner(db, user, collection):
        raise HTTPException(status_code=401, detail="Unauthorized")
    else:
        return user

@router.post(
    "/upsert-file/{collection}",
    response_model=UpsertResponse,
)
async def upsert_file(
    collection: UUID,
    file: UploadFile = File(...),
    metadata: Optional[str] = Form(None),
    file_name: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user: str = Depends(validate_user),
):

    try:
        metadata_obj = (
            DocumentMetadata.parse_raw(metadata)
            if metadata
            else DocumentMetadata(source=Source.file)
        )
    except:
        metadata_obj = DocumentMetadata(source=Source.file)

    document, file_space = await get_document_from_file(file, metadata_obj)

    sum_file_size = crud.get_total_file_size(db, user)

    file_limit = crud.get_file_limit(db, user)

    if (sum_file_size + file_space) > file_limit:
        raise HTTPException(status_code=429, detail="File size limit exceeded")
    
    document_id = crud.create_file(db, schemas.DocumentFileCreate(file_name=file_name, collection_id=collection, file_size=file_space))
    metadata_obj.source_id = str(document_id)
    
    try:
        ids = await datastore.upsert([document], collection_name=str(collection))
        return UpsertResponse(ids=ids)
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail=f"str({e})")


@router.post(
    "/query/{collection}",
    response_model=QueryResponse,
)
async def query_main(
    collection: UUID,
    request: QueryRequest = Body(...),
    user: str = Depends(validate_user),
):
    try:
        results = await datastore.query(
            request.queries,
            str(collection)
        )
        return QueryResponse(results=results)
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail="Internal Service Error")


@router.post(
    "/upsert/{collection}",
    response_model=UpsertResponse,
)
async def upsert(
    collection: UUID,
    request: UpsertRequest = Body(...),
    user: str = Depends(validate_user),
):

    try:
        ids = await datastore.upsert(request.documents, collection_name=str(collection))
        return UpsertResponse(ids=ids)
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail="Internal Service Error")


@router.post(
    "/delete/{collection}",
    response_model=DeleteResponse,
)
async def delete(
    collection: UUID,
    request: DeleteRequest = Body(...),
    user: str = Depends(validate_user),
    db: Session = Depends(get_db),
):
    try:
        success = await datastore.delete(
            ids=request.ids,
            filter=request.filter,
            delete_all=request.delete_all,
            collection_name=str(collection)
        )

        if request.filter is not None and request.filter.source_id is not None:
            crud.delete_file(db, request.filter.source_id)

        if request.delete_all:
            crud.delete_collection(db, collection)

        return DeleteResponse(success=success)
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail="Internal Service Error")

@router.put(
    "/collection",
    response_model=CreateCollectionResponse,
)
def creat_collection(
    request: CreateCollectionRequest = Body(...),
    user: str = Depends(validate_user_info),
    db: Session = Depends(get_db),
):
    try:
        collection_id = crud.create_collection(db, schemas.CollectionCreate(**request.dict(), owner=user))
        datastore.create_collection(collection_id)
        return CreateCollectionResponse(
            id=collection_id,
            owner=user,
            name=request.name,
            description=request.description
        )

    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail="Internal Service Error")

@router.get(
    "/collection",
    response_model=UserCollectionResponse,
)
def get_collection(
    user: str = Depends(validate_token),
    db: Session = Depends(get_db),
):
    try:
        collection = crud.get_collection(db, user)
        # print(collection)
        return UserCollectionResponse(
            owner=user,
            collections=collection
        )

    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail="Internal Service Error")

@router.get(
    "/collection/query",
    response_model=CollectionFileResponse,
)
def get_colletcion_file(
    collection_id: UUID,
    user: str = Depends(validate_token),
    db: Session = Depends(get_db),
):
    try:
        collection = crud.get_collection_by_id(db, collection_id)
        
        return CollectionFileResponse(
            id=collection.id,
            owner=collection.owner,
            name=collection.name,
            created_at=collection.created_at,
            updated_at=collection.updated_at,
            description=collection.description,
            documents=collection.documents,
            fallback_msg=collection.fallback_msg,
            line_channel_access_token=collection.line_channel_access_token,
            line_language=collection.line_language
        )

    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail="Internal Service Error")

@router.post(
    "/collection/update",
    response_model=UpdateCollectionResponse,
)
def update_collection(
    collection_id: UUID,
    request: CreateCollectionRequest = Body(...),
    user: str = Depends(validate_token),
    db: Session = Depends(get_db),
):
    try:
        collection = crud.update_collection(db, collection_id, schemas.CollectionCreate(**request.dict(), owner=user))

        return UpdateCollectionResponse(
            id=collection.id,
            owner=user,
            name=request.name,
            description=request.description,
            created_at=collection.created_at,
            updated_at=collection.updated_at,
            line_channel_access_token=request.line_channel_access_token,
            line_language=request.line_language,
            fallback_msg=collection.fallback_msg
        )

    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail="Internal Service Error")