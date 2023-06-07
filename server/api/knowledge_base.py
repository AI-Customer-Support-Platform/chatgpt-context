
from fastapi import (
    FastAPI, 
    File, 
    Form, 
    HTTPException, 
    Body, 
    UploadFile,
    Response,
    APIRouter
)
from typing import Optional, Annotated

from models.models import DocumentMetadata, Source
from models.api import (
    DeleteRequest,
    DeleteResponse,
    QueryRequest,
    QueryResponse,
    UpsertRequest,
    UpsertResponse,
)
from services.file import get_document_from_file
from datastore.providers.qdrant_datastore import QdrantDataStore

router = APIRouter()
datastore = QdrantDataStore()

@router.post(
    "/upsert-file/{collection}",
    response_model=UpsertResponse,
)
async def upsert_file(
    collection: str,
    file: UploadFile = File(...),
    metadata: Optional[str] = Form(None),
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

    try:
        ids = await datastore.upsert([document], collection_name=collection)
        return UpsertResponse(ids=ids)
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail=f"str({e})")


@router.post(
    "/query/{collection}",
    response_model=QueryResponse,
)
async def query_main(
    collection: str,
    request: QueryRequest = Body(...),
):
    try:
        results = await datastore.query(
            request.queries,
            collection
        )
        return QueryResponse(results=results)
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail="Internal Service Error")


@router.post(
    "/upsert/{collection}",
    response_model=UpsertResponse,
)
async def upsert(
    collection: str,
    request: UpsertRequest = Body(...),
):
    try:
        ids = await datastore.upsert(request.documents, collection_name=collection)
        return UpsertResponse(ids=ids)
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail="Internal Service Error")


@router.delete(
    "/delete/{collection}",
    response_model=DeleteResponse,
)
async def delete(
    collection: str,
    request: DeleteRequest = Body(...),
):
    if not (request.ids or request.filter or request.delete_all):
        raise HTTPException(
            status_code=400,
            detail="One of ids, filter, or delete_all is required",
        )
    try:
        success = await datastore.delete(
            ids=request.ids,
            filter=request.filter,
            delete_all=request.delete_all,
            collection_name=collection
        )
        return DeleteResponse(success=success)
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail="Internal Service Error")

@router.put(
    "/collection/{collection}",
    response_model=DeleteResponse,
)
def creat_collection(
    collection: str,
):
    try:
        flag = datastore.create_collection(collection)
        if flag:
            return DeleteResponse(success=True)
        else:
            return DeleteResponse(success=False)
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail="Internal Service Error")