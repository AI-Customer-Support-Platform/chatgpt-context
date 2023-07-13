import os
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
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
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
from server.db.database import SessionLocal, engine
from sqlalchemy.orm import Session

from auth0.authentication import Users
from auth0.exceptions import Auth0Error, TokenValidationError
from services.auth0 import TokenVerifier, AsymmetricSignatureVerifier

router = APIRouter()
datastore = QdrantDataStore()
cache = RedisChat()

bearer_scheme = HTTPBearer()

auth0_domain = os.environ.get('AUTH0_DOMAIN')
auth0_client_id = os.environ.get('AUTH_CLIENT_ID')
auth0_user = Users(auth0_domain)

auth0_sv = AsymmetricSignatureVerifier(f"https://{auth0_domain}/.well-known/jwks.json")
auth0_tv = TokenVerifier(signature_verifier=auth0_sv, issuer=f"https://{auth0_domain}/", audience=auth0_client_id)

models.Base.metadata.create_all(bind=engine)

def validate_user_info(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    if credentials.scheme != "Bearer":
        raise HTTPException(status_code=401, detail="Missing token")
    try:
        user_info = auth0_user.userinfo(credentials.credentials)
        if not user_info["email_verified"]:
            raise HTTPException(status_code=401, detail="Email Verification Required")
        user_id = auth0_user.userinfo(credentials.credentials)["sub"]
        # user_id = "test"
    except Auth0Error:
        raise HTTPException(status_code=401, detail="Invalid token")

    return user_id

def validate_token(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    if credentials.scheme != "Bearer":
        raise HTTPException(status_code=401, detail="Missing token")
    try:
        # print(credentials.credentials)
        user_info = auth0_tv.verify(credentials.credentials)
        user_id = user_info["sub"]
        # user_id = "test"
    except TokenValidationError:
        raise HTTPException(status_code=401, detail="Invalid token")

    return user_id

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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

    document = await get_document_from_file(file, metadata_obj)

    document_id = crud.create_file(db, schemas.DocumentFileCreate(file_name=file_name, collection_id=collection))
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
            documents=collection.documents
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
            updated_at=collection.updated_at
        )

    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail="Internal Service Error")