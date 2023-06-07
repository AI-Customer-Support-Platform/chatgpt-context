import os
import json
import uuid
import logging
import uvicorn
from fastapi import (
    FastAPI, 
    WebSocket, 
    WebSocketDisconnect, 
    HTTPException, 
    Depends, 
    Body,
    Cookie,
    Response,
)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from server.api import knowledge_base

from models.api import (
    ChatRequest,
    ChatResponse,
    ChatHistoryResponse,
    WebsocketMessage
)
from datastore.factory import get_datastore, get_redis

from services.chat import generate_chat_response, generate_chat_response_async, history_to_query
from services.i18n import i18nAdapter

from models.models import Query, AuthMetadata
from models.i18n import i18n

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

app.include_router(knowledge_base.router)

@app.get("/history/{user_id}", response_model=ChatHistoryResponse)
async def chat_history(response: Response, user_id: str):
    try:
        user_bytes = uuid.UUID(user_id).bytes
    except ValueError:
        raise HTTPException(status_code=500, detail="badly formed hexadecimal UUID string")

    if cache.user_exists(user_bytes):
        history = cache.get_qa_history(user_bytes)
        exist_flag = True

    else:
        history = []
        exist_flag = False

    return ChatHistoryResponse(
        user_id=user_id, 
        history=history, 
        exist=exist_flag
    )

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


@app.websocket("/ws/{collection}")
async def websocket_endpoint(collection: str, websocket: WebSocket):
    await websocket.accept()
    
    try:
        metadata_json = await websocket.receive_json()
        auth_metadata = AuthMetadata(**metadata_json)
    except:
        await websocket.close(1001, "authMetadata.decodeError")
        return
        
    if auth_metadata.auth != f"Bearer {BEARER_TOKEN}":
        await websocket.close(1002, "errors.unauthorized")
        return

    greeting = ""
    try:
        language=i18n(auth_metadata.language)
    except ValueError:
        language = "en"

    gretting_word = i18n_adapter.get_message(language, message="greetings")
    sorry = i18n_adapter.get_message(language, message="sorry")
    
    for word in gretting_word:
        greeting += word
        await websocket.send_text(greeting)
        
    await websocket.send_text("END")


    user_id = await websocket.receive_text()
    user_uuid = uuid.UUID(user_id).bytes
    await websocket.send_text("OK")

    while True:
        question_flag = True
        try:
            params = await websocket.receive_json()
        except WebSocketDisconnect:
            return
        except json.decoder.JSONDecodeError:
            await websocket.close()
            return

        try:
            auth_metadata = AuthMetadata(**params)
            language=i18n(auth_metadata.language)
            gretting_word = i18n_adapter.get_message(language, message="greetings")
            sorry = i18n_adapter.get_message(language, message="sorry")

            greeting = ""
            for word in gretting_word:
                greeting += word
                await websocket.send_text(greeting)
            
            await websocket.send_text("END")

            continue
        except:
            pass

        try:
            ask_request = ChatRequest(**params)
        except:
            await websocket.close(1007, "errors.invalidAskRequest")
            return
        question = ask_request.question
        print(f"{user_id} asked: {question}")

        if cache.user_exists(user_uuid):
            try:
                question = history_to_query(question, cache.get_chat_history(user_uuid))
                print(question)
            except AttributeError:
                question_flag = False
        
        if question_flag:
            query_results = await datastore.query(
                [Query(query=question, top_k=3)],
                collection
            )

            async for data in generate_chat_response_async(
                context=query_results[0].results, 
                question=question, sorry=i18n_adapter.get_message(language, "sorry")):

                await websocket.send_text(data)

            cache.set_chat_history(user_uuid, {
                "user_question": ask_request.question,
                "query": f"<search>{question}</search>",
                "background": f"<result>{query_results[0].results[0].text}</result>",
                "answer": data
            })
        else:
            error_content = ""
            for word in i18n_adapter.get_message(language, message="sorry_list"):
                error_content += word
                await websocket.send_text(error_content)
                
        await websocket.send_text("END")

@app.on_event("startup")
async def startup():
    global datastore
    datastore = await get_datastore()

    global cache
    cache = await get_redis()

    global i18n_adapter
    i18n_adapter = i18nAdapter("languages/local.json")


def start():
    uvicorn.run("server.main:app", host="0.0.0.0", port=8000, reload=True)
