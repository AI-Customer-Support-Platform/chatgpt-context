import os
from typing import Optional
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, File, Form, HTTPException, Depends, Body, UploadFile
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from models.api import (
    DeleteRequest,
    DeleteResponse,
    QueryRequest,
    QueryResponse,
    UpsertRequest,
    UpsertResponse,
    ChatRequest,
    ChatResponse,
)
from datastore.factory import get_datastore
from services.file import get_document_from_file
from services.chat import generate_chat_response

from models.models import DocumentMetadata, Source, Query

bearer_scheme = HTTPBearer()
BEARER_TOKEN = os.environ.get("BEARER_TOKEN")
assert BEARER_TOKEN is not None


def validate_token(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    if credentials.scheme != "Bearer" or credentials.credentials != BEARER_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    return credentials


app = FastAPI(dependencies=[Depends(validate_token)])
app.mount("/.well-known", StaticFiles(directory=".well-known"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create a sub-application, in order to access just the query endpoint in an OpenAPI schema, found at http://0.0.0.0:8000/sub/openapi.json when the app is running locally
sub_app = FastAPI(
    title="Retrieval Plugin API",
    description="A retrieval API for querying and filtering documents based on natural language queries and metadata",
    version="1.0.0",
    servers=[{"url": "https://your-app-url.com"}],
    dependencies=[Depends(validate_token)],
)
app.mount("/sub", sub_app)


@app.post(
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
    

@app.post(
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


@app.post(
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


@sub_app.post(
    "/query",
    response_model=QueryResponse,
    # NOTE: We are describing the shape of the API endpoint input due to a current limitation in parsing arrays of objects from OpenAPI schemas. This will not be necessary in the future.
    description="Accepts search query objects array each with query and optional filter. Break down complex questions into sub-questions. Refine results by criteria, e.g. time / source, don't do this often. Split queries if ResponseTooLargeError occurs.",
)
async def query(
    request: QueryRequest = Body(...),
):
    try:
        results = await datastore.query(
            request.queries,
        )
        return QueryResponse(results=results)
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail="Internal Service Error")

@app.post("/chat/{collection}", response_model=ChatResponse)
async def chat(
    collection: str,
    request: ChatRequest = Body(...),
):
    try:
        query_results = await datastore.query(
            [Query(query=request.question, topK=5)],
            collection
        )
        
        chat_response = generate_chat_response(
            context=query_results[0].results,
            question=request.question,
            model=request.model,
        )

        return ChatResponse(response=chat_response, model=request.model)
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail="Internal Service Error") 

@app.delete(
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

@app.put(
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

@app.on_event("startup")
async def startup():
    global datastore
    datastore = await get_datastore()


def start():
    uvicorn.run("server.main:app", host="0.0.0.0", port=8000, reload=True)
